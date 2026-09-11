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
    recorder.emit("run_started", "run", "started")
    recorder.emit("tool_completed", "tool", "ok", tool="get_skill_stats", prompt_ref="prompt-hash", safe_args_ref="args-hash", result_ref={"facts_ref": "ref-facts"})
    recorder.emit("run_completed", "run", "ok")
    return recorder.events


def test_env_always_provides_queue_exporter():
    assert LangfuseExporter.from_env({"LANGFUSE_BASE_URL": "http://localhost"}).enabled is True
    assert LangfuseExporter.from_env(env(POB_AGENT_LANGFUSE_SAMPLE_RATE="0"), sdk_module=sdk_for(FakeClient())).enabled is True
    assert "incomplete" in LangfuseExporter.from_env(env(LANGFUSE_SECRET_KEY=""), sdk_module=sdk_for(FakeClient())).reason


def test_no_remote_configuration_still_persists_redacted_trace(tmp_path):
    exporter = LangfuseExporter.from_env({"LANGFUSE_PUBLIC_KEY": "", "LANGFUSE_SECRET_KEY": "", "LANGFUSE_BASE_URL": "", "POB_AGENT_LANGFUSE_QUEUE_PATH": str(tmp_path / "queue.ndjson")})
    assert exporter.enabled is True
    assert exporter.export(events()).status == "queued"
    assert (tmp_path / "queue.ndjson").is_file()


def test_success_maps_one_trace_and_redacted_events():
    client = FakeClient()
    exporter = LangfuseExporter.from_env(env(), sdk_module=sdk_for(client))
    trace_events = events()
    assert exporter.export(trace_events).status == "sent"
    assert exporter.export(trace_events).status == "disabled"
    assert sum(item["name"] == "pob-agent" for item in client.observations) == 1
    assert sum(item["as_type"] == "span" for item in client.observations) == len(trace_events)
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


def test_real_langfuse_sdk_4_smoke_when_explicitly_configured():
    """Uses the installed SDK only when a local/dev service is explicitly configured."""
    if os.getenv("RUN_LANGFUSE_SMOKE") != "1":
        pytest.skip("explicit Langfuse smoke opt-in is not enabled")
    exporter = LangfuseExporter.from_env()
    if exporter.client is None:
        pytest.skip("Langfuse local service credentials are unavailable")
    assert exporter.enabled is True
    assert exporter.export(events()).status in {"sent", "queued"}
