"""stdio and Streamable HTTP transports for the canonical PoE tool catalog."""

from __future__ import annotations

import json
import logging
import asyncio
import hmac
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool, ToolAnnotations, CallToolResult

from agent.orchestration.function_trace import FunctionTrace, trace_pipeline
from agent.mcp.handlers import _error, create_handlers, current_snapshot
from agent.tool_catalog import TOOL_CATALOG


def create_server(*, endpoint_dir=None, knowledge_search=None, external_search=None, transport=None):
    server = Server("path-of-building-agent", version="1.0.0")
    handlers = create_handlers(endpoint_dir, knowledge_search, external_search, transport=transport)

    def request_trace_headers():
        try:
            request = server.request_context.request
        except LookupError:
            return {}
        return request.headers if request is not None else {}

    @server.list_tools()
    @trace_pipeline(context_provider=request_trace_headers)
    async def list_tools():
        return [Tool(name=spec.name, description=spec.description, inputSchema=spec.input_schema,
                     annotations=ToolAnnotations(**spec.as_mcp_definition()["annotations"]))
                for spec in TOOL_CATALOG.values()]

    @server.call_tool()
    @trace_pipeline(context_provider=request_trace_headers)
    async def call_tool(name: str, arguments: dict):
        spec = TOOL_CATALOG.get(name)
        if spec is None or name not in handlers:
            result = _error("TOOL_NOT_FOUND", "unknown tool: " + str(name), stage="mcp_dispatch")
        else:
            try:
                result = await asyncio.wait_for(asyncio.to_thread(handlers[name], arguments),
                                                timeout=spec.timeout_seconds)
            except asyncio.TimeoutError:
                result = _error("TIMEOUT", f"Tool exceeded its {spec.timeout_seconds}s deadline", stage="mcp_timeout")
        failed = isinstance(result, dict) and isinstance(result.get("error"), dict)
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, separators=(",", ":")))],
                              isError=failed)

    @server.list_resources()
    @trace_pipeline(context_provider=request_trace_headers)
    async def list_resources():
        return [Resource(uri="pob://current-snapshot", name="Current PoB snapshot",
                         description="Fresh normalized context from the active Path of Building session",
                         mimeType="application/json")]

    @server.read_resource()
    @trace_pipeline(context_provider=request_trace_headers)
    async def read_resource(uri):
        if str(uri) != "pob://current-snapshot":
            raise ValueError("unknown MCP resource")
        return json.dumps(current_snapshot(transport), ensure_ascii=False, separators=(",", ":"))

    return server


def create_http_app(server=None, *, token=None):
    """Create a private Streamable HTTP MCP endpoint for Compose networking."""
    from contextlib import asynccontextmanager
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    server = server or create_server()
    token = token if token is not None else os.environ.get("POB_AGENT_MCP_TOKEN", "")
    if not token:
        raise RuntimeError("POB_AGENT_MCP_TOKEN is required for Streamable HTTP mode")
    manager = StreamableHTTPSessionManager(app=server, json_response=True)

    async def health(_request):
        return JSONResponse({"status": "ok"})

    @asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    application = Starlette(routes=[
        Route("/healthz", health, methods=["GET"]),
        Mount("/mcp", app=StreamableHTTPASGIApp(manager)),
    ], lifespan=lifespan)

    class BearerTokenMiddleware:
        def __init__(self, app): self.app = app
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http" or scope.get("path") == "/healthz":
                return await self.app(scope, receive, send)
            headers = dict(scope.get("headers", []))
            supplied = headers.get(b"authorization", b"").decode("latin1")
            expected = "Bearer " + token
            if not hmac.compare_digest(supplied, expected):
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                return await response(scope, receive, send)
            run_id = headers.get(b"x-pob-trace-run-id", b"").decode("ascii", errors="ignore")
            parent_id = headers.get(b"x-pob-trace-parent-id", b"").decode("ascii", errors="ignore")
            with FunctionTrace("agent.mcp.request", {"scope": scope, "receive": receive, "send": send},
                               run_id=run_id or None, parent_id=parent_id or None):
                await self.app(scope, receive, send)

    return BearerTokenMiddleware(application)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server = create_server()
    if os.environ.get("POB_AGENT_MCP_TRANSPORT", "stdio") == "streamable-http":
        import uvicorn
        app = create_http_app(server)
        uvicorn.run(app, host=os.environ.get("POB_AGENT_MCP_HOST", "0.0.0.0"),
                    port=int(os.environ.get("POB_AGENT_MCP_PORT", "8000")), log_level="info")
    else:
        async def run():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())
        asyncio.run(run())


if __name__ == "__main__":
    main()
