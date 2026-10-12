"""Synchronous facade over one persistent MCP stdio or Streamable HTTP session."""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import os
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from agent.mcp.errors import ToolCallError
from agent.tool_catalog import ALLOWED_TOOLS, TOOL_CATALOG


class McpClientError(RuntimeError):
    pass


class McpToolClient:
    def __init__(self, *, command=None, args=None, cwd=None, env=None, url=None, token=None, timeout=30):
        self.command = command or __import__("sys").executable
        self.args = args or ["-m", "agent.mcp.server"]
        self.cwd = cwd
        self.env = env
        self.url = url or os.environ.get("POB_AGENT_MCP_URL")
        self.token = token if token is not None else os.environ.get("POB_AGENT_MCP_TOKEN")
        self.timeout = timeout
        self._thread = None
        self._loop = None
        self._ready = threading.Event()
        self._failure = None
        self._session = None
        self._shutdown = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return self
        self._ready.clear()
        self._failure = None
        self._thread = threading.Thread(target=self._run_loop, name="poe-mcp-client", daemon=True)
        self._thread.start()
        if not self._ready.wait(self.timeout):
            raise McpClientError("MCP server startup timed out")
        if self._failure:
            raise McpClientError("MCP server startup failed: " + str(self._failure)) from self._failure
        return self

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._shutdown = asyncio.Event()
        self._loop.run_until_complete(self._session_lifecycle())
        self._loop.close()

    async def _session_lifecycle(self):
        try:
            async with AsyncExitStack() as stack:
                if self.url:
                    headers = {"Authorization": "Bearer " + self.token} if self.token else None
                    http_timeout = max(self.timeout, max(spec.timeout_seconds for spec in TOOL_CATALOG.values()) + 5)
                    streams = await stack.enter_async_context(streamablehttp_client(
                        self.url, headers=headers, timeout=http_timeout))
                else:
                    params = StdioServerParameters(command=self.command, args=self.args, cwd=self.cwd, env=self.env)
                    streams = await stack.enter_async_context(stdio_client(params))
                session = await stack.enter_async_context(ClientSession(*streams[:2]))
                self._session = session
                await session.initialize()
                self._ready.set()
                await self._shutdown.wait()
        except BaseException as error:
            self._failure = error
            self._ready.set()
        finally:
            self._session = None

    def _submit(self, coroutine, timeout=None):
        if not self._loop or not self._thread or not self._thread.is_alive():
            raise McpClientError("MCP client is not running")
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)
        try:
            return future.result(self.timeout if timeout is None else timeout)
        except Exception as error:
            raise McpClientError(str(error)) from error

    def list_tools(self):
        result = self._submit(self._session.list_tools())
        tools = [item.model_dump(by_alias=True) for item in result.tools]
        actual = {item["name"] for item in tools}
        if actual != set(ALLOWED_TOOLS):
            raise McpClientError("MCP tool catalog does not match AgentLoop allowlist")
        return tools

    def call_tool(self, name, arguments):
        spec = TOOL_CATALOG.get(name)
        call_timeout = (spec.timeout_seconds + 5) if spec else self.timeout
        result = self._submit(self._session.call_tool(name, arguments), timeout=call_timeout)
        for item in result.content:
            if getattr(item, "type", None) == "text":
                try:
                    payload = json.loads(item.text)
                except (json.JSONDecodeError, TypeError):
                    payload = {"text": item.text}
                if result.isError:
                    error = payload.get("error", payload) if isinstance(payload, dict) else {"message": str(payload)}
                    raise ToolCallError(error)
                return payload
        if result.isError:
            raise ToolCallError({"code": "UNCLASSIFIED_FAILURE", "message": "MCP tool call failed"})
        return {"content": [item.model_dump() for item in result.content], "isError": result.isError}

    def read_resource(self, uri="pob://current-snapshot"):
        result = self._submit(self._session.read_resource(uri))
        if not result.contents:
            raise McpClientError("MCP resource returned no contents")
        first = result.contents[0]
        text = getattr(first, "text", None)
        if not isinstance(text, str):
            raise McpClientError("MCP snapshot resource was not text")
        try:
            return json.loads(text)
        except json.JSONDecodeError as error:
            raise McpClientError("MCP snapshot resource returned invalid JSON") from error

    def close(self):
        if self._loop and self._thread and self._thread.is_alive():
            self._loop.call_soon_threadsafe(self._shutdown.set)
            self._thread.join(timeout=self.timeout)
            self._thread = None


class McpSearchFacade:
    """Adapter for AgentLoop's legacy search/alias injection interface."""
    def __init__(self, client): self.client = client
    def search(self, query, limit=10, category=None, include_non_authoritative=False):
        return self.client.call_tool("search_knowledge", {"query": query, "limit": limit, **({"category": category} if category else {})})
    def resolve_item_alias(self, query, category=None):
        args = {"query": query, **({"category": category} if category else {})}
        return self.client.call_tool("resolve_item_alias", args)
    def resolve_skill_alias(self, query): return self.client.call_tool("resolve_skill_alias", {"query": query})
