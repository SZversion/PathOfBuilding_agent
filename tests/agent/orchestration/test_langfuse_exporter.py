import json
import contextlib
import os
import pathlib
import sys
import types
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop
from agent.orchestration.langfuse_exporter import LangfuseExporter
from agent.orchestration.trace import TraceRecorder


class FakeClient:
    def __init__(self, fail_flush=False, fail_close=False):
        self.observations = []
        self.fail_flush = fail_flush
        self.fail_close = fail_close

    @contextlib.contextmanager
    def start_as_current_observation(self, **kwargs):
        self.observations.append(kwargs)
        yield self

    def flush(self):
        if self.fail_flush:
            raise RuntimeError("flush")

    def shutdown(self):
        if self.fail_close:
            raise RuntimeError("close")


def sdk_for(client):
    return types.SimpleNamespace(__version__="4.2.0", Langfuse=lambda **kwargs: client)


def env(**extra):
    values = {"POB_AGENT_LANGFUSE_DEV_ENABLED": "1", "POB_AGENT_LANGFUSE_SAMPLE_RATE": "1", "LANGFUSE_PUBLIC_KEY": "public", "LANGFUSE_SECRET_KEY": "secret", "LANGFUSE_BASE_URL": "http://127.0.0.1:3000"}
    values.update(extra)
    return values


def events():
    recorder = TraceRecorder(request_id="req-1")
    recorder.set_snapshot("rev-1", "build-1")
    recorder.set_input({"question": "질문"})
    recorder.set_output("답변")
    recorder.emit("run_started", "run", "started")
    recorder.emit("tool_completed", "tool", "ok", tool="get_skill_stats", prompt_ref="prompt-hash", safe_args_ref="args-hash", result_ref={"facts_ref": "ref-facts"})
    recorder.emit("run_completed", "run", "ok")
    return recorder.events


def test_env_always_provides_queue_exporter():
    assert LangfuseExporter.from_env({"LANGFUSE_BASE_URL": "http://localhost"}).enabled is True
    assert LangfuseExporter.from_env(env(POB_AGENT_LANGFUSE_SAMPLE_RATE="0"), sdk_module=sdk_for(FakeClient())).enabled is True
    assert "incomplete" in LangfuseExporter.from_env(env(LANGFUSE_SECRET_KEY=""), sdk_module=sdk_for(FakeClient())).reason


def test_docker_service_host_requires_explicit_allowlist():
    values = env(LANGFUSE_BASE_URL="http://langfuse-web:3000")
    denied = LangfuseExporter.from_env(values, sdk_module=sdk_for(FakeClient()))
    allowed = LangfuseExporter.from_env({**values, "POB_AGENT_LANGFUSE_ALLOWED_HOSTS": "langfuse-web"},
                                        sdk_module=sdk_for(FakeClient()))
    assert "host must be local" in denied.reason
    assert allowed.reason == "enabled"


def test_no_remote_configuration_still_persists_redacted_trace(tmp_path):
    exporter = LangfuseExporter.from_env({"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": "", "LANGFUSE_BASE_URL": "", "POB_AGENT_LANGFUSE_QUEUE_PATH": str(tmp_path / "queue.ndjson")})
    assert exporter.enabled is True
    assert exporter.export(events()).status == "queued"
    assert (tmp_path / "queue.ndjson").is_file()


def test_success_maps_one_trace_and_redacted_events():
    client = FakeClient()
    exporter = LangfuseExporter.from_env(env(), sdk_module=sdk_for(client))
    trace_events = events()
    assert exporter.export(trace_events, input_payload={"question": "질문"}, output_payload="답변").status == "sent"
    assert exporter.export(trace_events).status == "disabled"
    assert sum(item["name"] == "pob-agent" for item in client.observations) == 1
    assert sum(item["as_type"] == "span" for item in client.observations) == len(trace_events)
    root = next(item for item in client.observations if item["name"] == "pob-agent")
    assert root["input"] == {"question": "질문"}
    assert root["output"] == "답변"
    text = json.dumps(client.observations, ensure_ascii=False)
    assert "public" not in text and "secret" not in text and "prompt-hash" in text
    assert "rev-1" in text and "ref-facts" in text


def test_missing_sdk_and_flush_close_failures_are_queued(tmp_path):
    assert LangfuseExporter.from_env(env(), sdk_module=object()).enabled is True
    flush = LangfuseExporter(FakeClient(fail_flush=True), enabled=True, reason="enabled", queue_path=tmp_path / "queue.ndjson")
    assert flush.export(events()).status == "queued"
    assert "ref-facts" in (tmp_path / "queue.ndjson").read_text(encoding="utf-8")
    close = LangfuseExporter(FakeClient(fail_close=True), enabled=True, reason="enabled", queue_path=tmp_path / "close.ndjson")
    assert close.export(events()).status == "queued"


def test_langfuse_safe_event_preserves_presentation_class():
    event = events()[0]
    event["presentation_class"] = "ask"
    safe = LangfuseExporter._safe_event(event)
    assert safe["presentation_class"] == "ask"


def test_localhost_is_required_and_queue_deduplicates_and_caps(tmp_path):
    assert LangfuseExporter.from_env(env(LANGFUSE_BASE_URL="https://langfuse.example"), sdk_module=sdk_for(FakeClient())).enabled is True
    path = tmp_path / "queue.ndjson"
    exporter = LangfuseExporter(FakeClient(fail_flush=True), enabled=True, reason="enabled", queue_path=path, queue_max_bytes=100000)
    trace_events = events()
    assert exporter.export(trace_events).status == "queued"
    assert exporter.export(trace_events).status == "disabled"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    capped = LangfuseExporter(FakeClient(fail_flush=True), enabled=True, reason="enabled", queue_path=tmp_path / "cap.ndjson", queue_max_bytes=1)
    assert capped.export(events()).status == "unavailable"


def test_agent_loop_exporter_failure_does_not_change_answer():
    class Model:
        model = "fake"
        endpoint = "https://agent.example.invalid/v1"

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[]}'
            return "답변"

    client = FakeClient(fail_flush=True)
    exporter = LangfuseExporter(client, enabled=True, reason="enabled")
    result = AgentLoop(Model(), trace_exporter=exporter).run("질문")
    assert result["status"] == "ok"


def test_agent_loop_exports_root_and_provider_input_output():
    class Model:
        model = "fake"
        endpoint = "http://127.0.0.1:11434/v1"

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","operation":"answer","evidenceLevel":"authoritative","required_evidence":[],"stop_condition":{},"steps":[]}'
            return "최종 답변"

    client = FakeClient()
    exporter = LangfuseExporter(client, enabled=True, reason="enabled")
    result = AgentLoop(Model(), trace_exporter=exporter).run("입출력 확인")
    assert result["status"] == "ok"
    root = next(item for item in client.observations if item["name"] == "pob-agent")
    assert root["input"]["question"] == "입출력 확인"
    assert root["output"]["response"] == result
    assert root["output"]["llm_outputs"][-1] == "최종 답변"
    planner = next(item for item in client.observations if item["name"] == "planner_started")
    assert planner["input"]["text"] == "입출력 확인"
    completed = next(item for item in client.observations if item["name"] == "run_completed")
    assert completed["input"]["question"] == "입출력 확인"
    assert completed["output"] == root["output"]
    provider_outputs = [item for item in client.observations if item["name"] == "generate"]
    assert all(item["as_type"] == "generation" for item in provider_outputs)
    assert any(item["output"] == "최종 답변" for item in provider_outputs)


def test_real_langfuse_sdk_4_smoke_when_explicitly_configured():
    """Uses the installed SDK only when a local/dev service is explicitly configured."""
    if os.getenv("RUN_LANGFUSE_SMOKE") != "1":
        pytest.skip("explicit Langfuse smoke opt-in is not enabled")
    exporter = LangfuseExporter.from_env()
    if exporter.client is None:
        pytest.skip("Langfuse local service credentials are unavailable")
    assert exporter.enabled is True
    assert exporter.export(events()).status in {"sent", "queued"}


def test_rejected_run_preserves_all_llm_json_and_response_fields():
    raw = {"schema_version": "1.0", "intent": "unknown", "operation": "answer",
           "evidenceLevel": "authoritative", "required_evidence": [],
           "stop_condition": {"type": "ask_user"}, "steps": [],
           "ambiguities": ["skill"], "metadata": {"nested": [None, {}, []]}}

    class Model:
        def chat(self, messages):
            return json.dumps(raw)

    client = FakeClient()
    result = AgentLoop(Model(), trace_exporter=LangfuseExporter(client, enabled=True)).run("질문")
    root = next(item for item in client.observations if item["name"] == "pob-agent")
    assert root["output"]["llm_outputs"] == [raw]
    assert root["output"]["response"] == result
    assert result["error"]["details"]
    provider = next(item for item in client.observations if item["name"] == "generate")
    assert provider["as_type"] == "generation"
    assert provider["output"] == raw


def test_export_payload_redacts_credentials_without_truncating_fields(tmp_path):
    payload = {"items": list(range(40)), "text": "x" * 300,
               "nested": {"authorization": "Bearer private", "api_key": "private", "value": None}}
    client = FakeClient()
    exporter = LangfuseExporter(client, enabled=True, queue_path=tmp_path / "queue.ndjson")
    assert exporter.export(events(), output_payload=payload).status == "sent"
    root = next(item for item in client.observations if item["name"] == "pob-agent")
    assert root["output"]["items"] == list(range(40))
    assert root["output"]["text"] == "x" * 300
    assert root["output"]["nested"] == {"authorization": "[REDACTED]", "api_key": "[REDACTED]", "value": None}


def test_export_uses_original_span_timestamps():
    import datetime

    class TimedExporter(LangfuseExporter):
        @contextlib.contextmanager
        def _observation(self, client, *, start_time=None, end_time=None, **kwargs):
            client.observations.append({**kwargs, "start_time": start_time, "end_time": end_time})
            yield client

    trace_events = events()
    for index, event in enumerate(trace_events):
        event["timestamp_utc"] = f"2026-10-12T07:00:0{index * 2}Z"
    trace_events[1]["duration_ms"] = 1500
    client = FakeClient()
    assert TimedExporter(client, enabled=True).export(trace_events).status == "sent"
    root = next(item for item in client.observations if item["name"] == "pob-agent")
    assert (root["end_time"] - root["start_time"]).total_seconds() == 4
    tool = next(item for item in client.observations if item["name"] == "tool_completed")
    assert (tool["end_time"] - tool["start_time"]).total_seconds() == 1.5
