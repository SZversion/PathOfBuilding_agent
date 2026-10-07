import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.mcp.client import McpToolClient
from agent.mcp.errors import ToolCallError


def test_stdio_server_lists_catalog_and_calls_capability_gated_mutation():
    root = pathlib.Path(__file__).parents[3]
    client = McpToolClient(command=sys.executable, cwd=root).start()
    try:
        tools = client.list_tools()
        assert len(tools) == 32
        assert all(item.get("inputSchema") for item in tools)
        replacement = next(item for item in tools if item["name"] == "replace_gem")
        assert replacement["annotations"]["readOnlyHint"] is False
        assert replacement["annotations"]["destructiveHint"] is False
        assert replacement["annotations"]["idempotentHint"] is False
        query = client.call_tool("search_knowledge", {"query": "Flicker Strike", "limit": 1})
        assert query["schema_version"] == "1.0"
        assert query["status"] == "ok"
        assert "facts" in query

        with pytest.raises(ToolCallError) as error:
            client.call_tool("replace_gem", {
                "socketGroup": 1, "gemIdentity": "test", "level": 20, "quality": 0,
                "expectedSnapshotRevision": "rev", "idempotencyKey": "key", "fingerprint": "fp",
            })
        assert error.value.error["code"] == "MUTATION_NOT_PERSISTENT"
        assert error.value.error["error_code"] == "MUTATION_NOT_PERSISTENT"
        assert error.value.error["recovery_class"] == "REJECT"
    finally:
        client.close()
