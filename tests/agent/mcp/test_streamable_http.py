import pathlib
import socket
import sys
import threading
import time

import pytest
import uvicorn

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.mcp.client import McpToolClient
from agent.mcp.server import create_http_app, create_server


class FakeKnowledge:
    def search(self, query, **kwargs): return {"query": query, **kwargs}
    def resolve_item_alias(self, query, category=None): return {"query": query, "category": category}
    def resolve_skill_alias(self, query): return {"query": query}


class FakeExternal:
    def search(self, query, source="both", limit=3): return {"query": query, "source": source, "limit": limit}


def test_streamable_http_mcp_is_authenticated_and_compatible_with_backend_client():
    server_app = create_server(knowledge_search=FakeKnowledge(), external_search=FakeExternal())
    app = create_http_app(server_app, token="secret-test-token")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    web_server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical"))
    thread = threading.Thread(target=web_server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if web_server.started: break
            time.sleep(0.02)
        client = McpToolClient(url=f"http://127.0.0.1:{port}/mcp", token="secret-test-token", timeout=5).start()
        try:
            tools = client.list_tools()
            assert len(tools) == 32
            result = client.call_tool("search_knowledge", {"query": "ignite", "limit": 2})
            assert result["facts"]["query"] == "ignite"
        finally:
            client.close()

        import urllib.error
        from urllib.request import Request, urlopen
        request = Request(f"http://127.0.0.1:{port}/mcp", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urlopen(request, timeout=2)
        assert error.value.code == 401
    finally:
        web_server.should_exit = True
        thread.join(timeout=5)
