import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.orchestration.agent_loop import AgentLoop
from agent.providers.openai_compatible import OpenAICompatibleClient
from agent.providers.openai_compatible import ExternalModelError


class Response:
    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False

    def __iter__(self):
        return iter(self.chunks)

    def close(self):
        self.closed = True


def event(text):
    return ("data: " + json.dumps({"choices": [{"delta": {"content": text}}]}, ensure_ascii=False) + "\n\n").encode("utf-8")


def test_sse_reassembles_utf8_and_split_lines():
    payload = event("안녕") + b"data: [DONE]\n\n"
    response = Response([payload[:3], payload[3:9], payload[9:]])
    assert list(OpenAICompatibleClient._sse_events(response)) == [payload.split(b"\n\n")[0].decode("utf-8").split(": ", 1)[1], "[DONE]"]


def test_agent_loop_forwards_final_tokens_without_retry_or_duplicate():
    class Model:
        def __init__(self): self.chat_calls = 0; self.stream_calls = 0
        def chat(self, messages):
            self.chat_calls += 1
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})
        def stream_chat(self, messages):
            self.stream_calls += 1
            yield "안"
            yield "녕"

    model = Model()
    tokens = []
    result = AgentLoop(model).run("life?", handlers={"get_character_stats": lambda args: {"life": 1}}, on_token=tokens.append)
    assert result["answer"] == "안녕"
    assert tokens == ["안", "녕"]
    assert model.chat_calls == 1
    assert model.stream_calls == 1


def test_stream_failure_returns_partial_without_retry():
    class Model:
        def chat(self, messages):
            return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "answer", "evidenceLevel": "authoritative", "steps": [{"tool": "get_character_stats", "arguments": {}}]})
        def stream_chat(self, messages):
            yield "부분"
            raise ExternalModelError("stream stopped", code="TIMEOUT", retryable=False)

    tokens = []
    result = AgentLoop(Model()).run("life?", handlers={"get_character_stats": lambda args: {"life": 1}}, on_token=tokens.append)
    assert result["status"] == "partial"
    assert result["answer"] == "부분"
    assert tokens == ["부분"]
