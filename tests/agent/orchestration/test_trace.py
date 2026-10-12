import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop
from agent.orchestration.trace import TraceRecorder
from agent.providers.openai_compatible import ExternalModelError
from agent.pob.bridge import PobBridgeError, PobTimeoutError


class RecordingExporter:
    def __init__(self, raises=False):
        self.calls = []
        self.raises = raises

    def export(self, events):
        self.calls.append(list(events))
        if self.raises:
            raise RuntimeError("export unavailable")
        return {"status": "sent"}


def test_trace_schema_lifecycle_and_redaction():
    recorder = TraceRecorder(request_id="req-test")
    recorder.set_snapshot("rev-1", "build-1")
    recorder.emit("run_started", "run", "started")
    recorder.emit("tool_started", "tool", "started", tool="get_skill_stats", safe_args_ref=recorder.safe_args_ref({"itemText": "SECRET_ITEM", "skillName": "Arc", "prompt": "SECRET_PROMPT"}))
    recorder.emit("run_completed", "run", "ok")
    text = json.dumps(recorder.events, ensure_ascii=False)
    assert recorder.events[0]["request_id"] == "req-test"
    assert recorder.events[-1]["event"] == "run_completed"
    assert "SECRET_ITEM" not in text and "SECRET_PROMPT" not in text
    assert recorder.events[0]["snapshot"] == {"revision": "rev-1", "build_id": "build-1"}
    required = {"schema_version", "event_id", "run_id", "request_id", "event", "stage", "timestamp_utc", "duration_ms", "status", "attempt", "provider", "snapshot", "tool", "step_index", "tool_call_count", "retry_of", "plan_ref", "safe_args_ref", "error_ref", "result_ref"}
    assert required <= set(recorder.events[1])


def test_trace_bounds_preserve_terminal_event():
    recorder = TraceRecorder(max_events=4, max_bytes=100000)
    recorder.emit("run_started", "run", "started")
    for _ in range(20):
        recorder.emit("tool_started", "tool", "started")
    recorder.emit("run_completed", "run", "ok")
    assert len(recorder.events) <= 4
    assert recorder.events[-1]["event"] == "run_completed"
    assert any(item["event"] == "trace_overflow" for item in recorder.events)


def test_recorder_failure_is_fail_safe():
    recorder = TraceRecorder()
    recorder._append = lambda event: (_ for _ in ()).throw(RuntimeError("trace failure"))
    recorder.emit("run_started", "run", "started")
    assert recorder._warning.startswith("recorder_failure:")


def test_agent_loop_connects_plan_tool_final_trace_without_sensitive_payload():
    class Model:
        model = "fake-model"
        endpoint = "https://user:secret@example.invalid/v1"

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[{"tool":"get_skill_stats","arguments":{"itemText":"PRIVATE"}}]}'
            return "한국어 답변"

    result = AgentLoop(Model()).run("질문 notes=PRIVATE", handlers={"get_skill_stats": lambda args: {"facts": {"value": 10}}}, snapshot={"buildId": "build-1", "config": {"secret": "PRIVATE"}})
    events = result["trace"]
    names = [event["event"] for event in events]
    assert names[0] == "run_started" and "planner_completed" in names and "tool_completed" in names and names[-1] == "run_completed"
    text = json.dumps(events, ensure_ascii=False)
    assert "PRIVATE" not in text and "secret@example" not in text and "itemText" not in text


def test_trace_records_provider_retry_and_tool_failure():
    class RetryModel:
        model = "retry-model"
        endpoint = "https://agent.example.invalid/v1"

        def __init__(self):
            self.calls = 0

        def chat(self, messages):
            self.calls += 1
            if self.calls == 1:
                raise ExternalModelError("temporary", code="MODEL_TRANSIENT")
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[{"tool":"get_skill_stats","arguments":{}}]}'
            return "실패를 설명합니다"

    result = AgentLoop(RetryModel()).run("질문", handlers={"get_skill_stats": lambda args: (_ for _ in ()).throw(RuntimeError("tool failed"))})
    names = [event["event"] for event in result["trace"]]
    assert "provider_failed" in names and "provider_completed" in names and "tool_failed" in names


def test_trace_records_each_tool_retry_and_timeout_status():
    class Model:
        model = "fake"
        endpoint = "https://agent.example.invalid/v1"

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[{"tool":"get_skill_stats","arguments":{}}]}'
            return "partial"

    calls = {"count": 0}

    def transient_tool(args):
        calls["count"] += 1
        if calls["count"] < 3:
            raise PobTimeoutError("temporary timeout")
        return {"evidenceGraph": {"nodes": [{"id": calls["count"]}]}, "facts": {"value": calls["count"]}}

    result = AgentLoop(Model()).run("q", handlers={"get_skill_stats": transient_tool})
    tool_events = [event for event in result["trace"] if event["event"].startswith("tool_")]
    assert len([event for event in tool_events if event["event"] == "tool_started"]) == 3
    assert any(event["retry_of"] for event in tool_events if event["event"] == "tool_started")

    def timeout_tool(args):
        raise TimeoutError("deadline")

    timeout = AgentLoop(Model()).run("q", handlers={"get_skill_stats": timeout_tool})
    failures = [event for event in timeout["trace"] if event["event"] == "tool_failed"]
    assert failures[-1]["status"] == "timeout"


def test_partial_outcome_and_value_based_result_refs():
    class Model:
        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[{"tool":"get_skill_stats","arguments":{}}]}'
            return "부분 답변"

    result = AgentLoop(Model()).run("q", handlers={"get_skill_stats": lambda args: (_ for _ in ()).throw(RuntimeError("failed"))})
    assert result["status"] == "partial"
    recorder = TraceRecorder()
    assert recorder.result_refs({"facts": {"value": 1}}) != recorder.result_refs({"facts": {"value": 2}})


def test_provider_timeout_is_recorded_as_timeout():
    class TimeoutModel:
        model = "timeout-model"
        endpoint = "https://agent.example.invalid/v1"

        def chat(self, messages):
            raise TimeoutError("provider deadline")

    result = AgentLoop(TimeoutModel()).run("q")
    failures = [event for event in result["trace"] if event["event"] == "provider_failed"]
    assert failures and failures[-1]["status"] == "timeout"
    assert failures[-1]["error_ref"] == "TIMEOUT"


def test_agent_loop_exports_once_for_success_planner_reject_and_planner_fail():
    class SuccessModel:
        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[]}'
            return "답변"

    class RejectModel:
        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"bad","steps":[{"tool":"unknown_tool","arguments":{}}]}'
            return "답변"

    class FailModel:
        def chat(self, messages):
            raise RuntimeError("planner unavailable")

    for model, expected_status in ((SuccessModel(), "ok"), (RejectModel(), "error"), (FailModel(), "plan_error")):
        exporter = RecordingExporter()
        result = AgentLoop(model, trace_exporter=exporter).run("질문")
        assert result["status"] == expected_status
        assert len(exporter.calls) == 1
        assert exporter.calls[0][-1]["event"] == "run_completed"


def test_exporter_failure_does_not_change_terminal_results():
    class Model:
        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[]}'
            raise RuntimeError("final unavailable")

    exporter = RecordingExporter(raises=True)
    result = AgentLoop(Model(), trace_exporter=exporter).run("질문")
    assert result["status"] == "error"
    assert len(exporter.calls) == 1
    assert exporter.calls[0][-1]["event"] == "run_completed"


def test_planner_rejects_unknown_skill_argument_then_repairs():
    class Model:
        def __init__(self):
            self.plans = 0

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                self.plans += 1
                if self.plans == 1:
                    return '{"intent":"stat","steps":[{"tool":"get_skill_dps","arguments":{"skill":"Arc"}}]}'
                return '{"intent":"stat","steps":[{"tool":"get_skill_dps","arguments":{}}]}'
            return "복구된 답변"

    model = Model()
    result = AgentLoop(model).run("질문", handlers={"get_skill_dps": lambda args: {"facts": {"value": 1}}})
    assert result["status"] == "ok"
    assert model.plans == 2
    assert any(event["event"] == "planner_failed" for event in result["trace"])


def test_authoritative_tool_failure_forbids_model_guess():
    class Model:
        def __init__(self):
            self.final_called = False

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"intent":"stat","steps":[{"tool":"get_skill_dps","arguments":{}}]}'
            self.final_called = True
            return "임의의 숫자"

    model = Model()
    result = AgentLoop(model).run("질문", handlers={"get_skill_dps": lambda args: (_ for _ in ()).throw(PobBridgeError("PoB unavailable", "VALUE_UNAVAILABLE"))})
    assert result["status"] == "partial"
    assert model.final_called is False
    assert result["uncertainty"]["code"] in {"VALUE_UNAVAILABLE", "POB_CALCULATION_ERROR"}
    assert "추측하지 않습니다" in result["answer"]
