import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.mcp.handlers import create_handlers, current_snapshot
from agent.pob.live_transport import LivePobTransportError
from agent.tool_catalog import ALLOWED_TOOLS


class FakeTransport:
    def __init__(self):
        self.calls = []

    def request(self, payload):
        self.calls.append(payload)
        return {"ok": True, "result": {"tool": payload["op"], "arguments": payload["arguments"]}}


class FakeKnowledge:
    def search(self, query, **kwargs): return {"query": query, **kwargs}
    def resolve_item_alias(self, query, category=None): return {"query": query, "category": category}
    def resolve_skill_alias(self, query): return {"query": query}


class FakeExternal:
    def search(self, query, source="both", limit=3): return {"query": query, "source": source, "limit": limit}


def test_handlers_cover_catalog_and_route_by_group():
    transport = FakeTransport()
    handlers = create_handlers(knowledge_search=FakeKnowledge(), external_search=FakeExternal(), transport=transport)

    assert set(handlers) == set(ALLOWED_TOOLS)
    assert handlers["get_skill_dps"]({"skillIndex": 2})["facts"]["tool"] == "get_skill_dps"
    assert handlers["search_knowledge"]({"query": "ignite"})["facts"]["query"] == "ignite"
    assert handlers["search_external"]({"query": "ignite", "source": "poewiki"})["facts"]["source"] == "poewiki"
    rejected = handlers["replace_gem"]({"socketGroup": 1, "gemIdentity": "x", "level": 20, "quality": 0,
        "expectedSnapshotRevision": "r", "idempotencyKey": "k", "fingerprint": "f"})
    assert rejected["error"]["code"] == "MUTATION_NOT_PERSISTENT"
    assert all(call["op"] != "replace_gem" for call in transport.calls)


def test_snapshot_resource_fetches_fresh_context():
    transport = FakeTransport()

    assert current_snapshot(transport)["tool"] == "capture_snapshot"
    assert transport.calls == [{"op": "capture_snapshot", "arguments": {}}]


def test_handler_boundary_validates_arguments():
    handlers = create_handlers(knowledge_search=FakeKnowledge(), external_search=FakeExternal(), transport=FakeTransport())

    result = handlers["search_external"]({"query": "x", "limit": 4})

    assert result["error"]["code"] == "INPUT_INVALID"
    assert result["status"] == "error"
    assert result["error"]["error_code"] == "INPUT_INVALID"


def test_live_transport_failure_is_structured_and_does_not_fall_back():
    class OfflineTransport:
        def request(self, payload): raise LivePobTransportError("no endpoint")

    handlers = create_handlers(knowledge_search=FakeKnowledge(), external_search=FakeExternal(), transport=OfflineTransport())

    result = handlers["get_character_stats"]({})

    assert result["error"]["code"] == "VALUE_UNAVAILABLE"


def test_handler_success_uses_envelope_and_preserves_existing_evidence():
    class EvidenceTransport:
        def request(self, payload):
            return {"ok": True, "result": {"status": "ok", "facts": {"dps": 12},
                "trace": [{"path": "CalcDPS"}], "snapshotRevision": "r1"}}

    handlers = create_handlers(knowledge_search=FakeKnowledge(), external_search=FakeExternal(), transport=EvidenceTransport())
    result = handlers["get_character_stats"]({})
    assert result["facts"] == {"dps": 12}
    assert result["trace"] == [{"path": "CalcDPS"}]
    assert result["snapshotRevision"] == "r1"
    assert result["schema_version"] == "1.0"
    assert result["evidenceGraph"] == {"nodes": [], "stages": [], "sourceEdges": []}
