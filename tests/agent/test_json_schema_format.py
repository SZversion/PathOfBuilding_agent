import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.orchestration.agent_loop import AgentLoop, EVIDENCE_LEVEL_ENUM, INTENT_ENUM, OPERATION_ENUM, PLANNER_JSON_SCHEMA, READ_ONLY_TOOLS
from agent.providers.ollama import OllamaDevelopmentProvider


def test_planner_only_receives_json_schema_format():
    class Model:
        supports_json_schema = True
        def __init__(self): self.formats = []
        def chat(self, messages, **kwargs):
            self.formats.append(kwargs.get("format"))
            if len(self.formats) == 1:
                return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})
            return "답변"

    model = Model()
    result = AgentLoop(model).run("life?", handlers={"get_character_stats": lambda args: {"life": 1}})
    assert result["status"] == "ok"
    assert isinstance(model.formats[0], dict)
    assert model.formats[1] is None


def test_ollama_format_rejection_falls_back_without_format(monkeypatch):
    requests = []
    class Response:
        def __init__(self, status=200): self.status = status
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps({"message": {"content": "ok"}}).encode()
    def fake_urlopen(request, timeout):
        requests.append(json.loads(request.data))
        if len(requests) == 1:
            from urllib.error import HTTPError
            raise HTTPError(request.full_url, 400, "format unsupported", {}, None)
        return Response()
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaDevelopmentProvider()
    assert provider.chat([], format={"type": "object"}) == "ok"
    assert "format" in requests[0]
    assert "format" not in requests[1]


def test_planner_schema_matches_validator_enums_and_read_only_steps():
    props = PLANNER_JSON_SCHEMA["properties"]
    assert set(props["intent"]["enum"]) == set(INTENT_ENUM)
    assert set(props["operation"]["enum"]) == set(OPERATION_ENUM)
    assert set(props["evidenceLevel"]["enum"]) == set(EVIDENCE_LEVEL_ENUM)
    step = props["steps"]["items"]
    step_props = step["properties"]
    assert set(step_props["tool"]["enum"]) == set(READ_ONLY_TOOLS)
    assert not {"replace_item", "replace_gem", "change_passive"} & set(step_props["tool"]["enum"])
    assert step["required"] == ["tool", "arguments"]
    assert step_props["arguments"]["type"] == "object"


def test_planner_prompt_and_schema_require_nonempty_ambiguities_for_ask_user():
    assert PLANNER_JSON_SCHEMA["properties"]["ambiguities"]["items"]["minLength"] == 1
    assert any("ask_user" in str(rule) and "ambiguities" in str(rule) for rule in PLANNER_JSON_SCHEMA["allOf"])
    from agent.orchestration.agent_loop import PLANNER_SYSTEM
    assert "EVERY missing or conflicting field" in PLANNER_SYSTEM
    assert "must never contain vague phrases" in PLANNER_SYSTEM
    assert '"ambiguities":[]' in PLANNER_SYSTEM


def test_ollama_native_chat_and_stream_use_api_chat(monkeypatch):
    requests = []
    class Response:
        def __init__(self, body): self.body = body
        def read(self): return self.body
        def __iter__(self): return iter([self.body])
        def close(self): pass
    def fake(request, timeout):
        requests.append((request.full_url, json.loads(request.data)))
        if requests[-1][1].get("stream"):
            return Response(b'{"message":{"content":"A"}}\n{"message":{"content":"B"},"done":true}\n')
        return Response(b'{"message":{"content":"ok"}}')
    monkeypatch.setattr("urllib.request.urlopen", fake)
    provider = OllamaDevelopmentProvider()
    assert provider.chat([], format={"type": "object"}) == "ok"
    assert list(provider.stream_chat([])) == ["A"]
    assert all(url.endswith("/api/chat") for url, _ in requests)
    assert requests[0][1]["format"] == {"type": "object"}
    assert requests[0][1]["model"] == "qwen3:8b"
    assert requests[0][1]["messages"] == []
    assert requests[1][1]["stream"] is True
