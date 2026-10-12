import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.orchestration.recovery import recover_response, safe_context, normalized_details


def error(recovery_class):
    return {"status": "error", "error": {"code": "X", "recovery_class": recovery_class, "next_action": "act", "details": {"reason": "why", "missing_fields": ["skill"], "prompt": "do not leak"}}}


def test_recovery_templates_and_safe_context():
    result = recover_response(error("ASK_USER"))
    assert result["answer"].startswith("추가 정보가 필요합니다")
    assert "prompt" not in safe_context(result["error"])
    assert "X" in recover_response(error("REPAIR_INPUT"))["answer"]
    assert "X" in recover_response(error("REFRESH_CONTEXT"))["answer"]


def test_recovery_model_failure_uses_template():
    class Broken:
        def chat(self, messages):
            raise RuntimeError("unavailable")
    result = recover_response(error("REJECT"), Broken())
    assert result["answer"].startswith("요청을 처리하지 못했습니다")


def test_recovery_context_redacts_nested_values_and_trace_matches_schema():
    value = error("REPAIR_INPUT")
    value["error"]["details"] = {"reason": {"nested": {"api_key": "secret", "text": "x" * 1000}}}
    result = recover_response(value)
    safe = safe_context(value["error"])
    assert "api_key" not in repr(safe)
    assert len(safe["reason"]["nested"]["text"]) <= 256
    value["trace"] = [{"run_id": "run-1", "request_id": "req-1", "provider": {}, "snapshot": {}}]
    traced = recover_response(value)
    event = traced["trace"][-1]
    assert event["event"] == "recovery_response"
    for field in ("schema_version", "event_id", "run_id", "request_id", "timestamp_utc", "status", "error_ref", "result_ref"):
        assert field in event


def test_recovery_details_are_standardized_and_candidates_are_display_only():
    value = error("ASK_USER")
    value["error"]["details"] = {"missing_fields": ["skillName"], "invalid_fields": ["level"], "expected_format": "string", "examples": ["Arc"], "candidates": [{"display": "뇌동의 연쇄번개", "id": 123}, {"name": "Arc"}], "prompt": "secret"}
    details = normalized_details(value["error"])
    assert details["candidates"] == ["뇌동의 연쇄번개", "Arc"]
    assert "123" not in repr(details)
    result = recover_response(value)
    assert "skillName" in result["answer"]
    assert "뇌동의 연쇄번개" in result["answer"]
    assert "prompt" not in result["error"]["details"]


def test_recovery_preserves_safe_legacy_detail_fields():
    value = error("REPAIR_INPUT")
    value["error"]["details"] = {"legacy_code": "old-format", "internal_id": "id-7", "token": "must-not-leak"}
    details = normalized_details(value["error"])
    assert details["legacy_code"] == "old-format"
    assert details["internal_id"] == "id-7"
    assert "token" not in details
