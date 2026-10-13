import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.orchestration.recovery import EXHAUSTED_ANSWER, exhausted_response, recover_response, safe_context, normalized_details
from agent.cli import _error
from agent.orchestration.runtime import _error_envelope
from agent.orchestration.state_store import StateStoreError


def error(recovery_class):
    return {"status": "error", "error": {"code": "X", "recovery_class": recovery_class, "next_action": "act", "details": {"reason": "why", "missing_fields": ["skill"], "prompt": "do not leak"}}}


def test_recovery_templates_and_safe_context():
    result = recover_response(error("ASK_USER"))
    assert result["answer"].startswith("추가 정보가 필요합니다")
    assert "prompt" not in safe_context(result["error"])
    repaired = recover_response(error("REPAIR_INPUT"))
    assert "입력 형식" in repaired["answer"]
    assert repaired["error"]["recovery_class"] == "ASK_USER"
    assert repaired["error"]["code"] == "X"
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
    assert result["error"]["details"]["confirmation_type"] == "ask"


def test_confirmation_presentation_is_traced_for_repair():
    value = error("REPAIR_INPUT")
    value["trace"] = [{"run_id": "run-1", "request_id": "req-1", "provider": {}, "snapshot": {}}]
    traced = recover_response(value)
    assert traced["error"]["code"] == "X"
    assert traced["error"]["recovery_class"] == "ASK_USER"
    assert traced["error"]["details"]["confirmation_type"] == "repair"
    assert traced["trace"][-1]["error_ref"] == "X"
    assert traced["trace"][-1]["presentation_class"] == "repair"


def test_recovery_trace_keeps_parent_and_leaf_error_refs():
    value = error("ASK_USER")
    value["error"]["code"] = "AMBIGUOUS_ALIAS"
    value["trace"] = [{"run_id": "run-1", "request_id": "req-1", "provider": {}, "snapshot": {}}]
    event = recover_response(value)["trace"][-1]
    assert event["error_ref"] == "AMBIGUOUS_CONTEXT"
    assert event["error_code"] == "AMBIGUOUS_ALIAS"


def test_all_input_error_envelopes_use_ask_user_boundary():
    for envelope in (_error("INPUT_INVALID", "bad"), _error_envelope("TOOL_NOT_FOUND", "REPAIR_INPUT", "plan", "bad"), _error_envelope("DUPLICATE_TOOL_CALL", "REPAIR_INPUT", "plan", "duplicate")):
        error_value = envelope["error"] if "error" in envelope else envelope
        assert error_value["recovery_class"] == "ASK_USER"
        assert error_value["next_action"] == "ask_user"
        assert error_value["details"]["confirmation_type"] == "repair"
    error_value = StateStoreError("bad", "INPUT_INVALID").error
    assert error_value["recovery_class"] == "ASK_USER"
    assert error_value["next_action"] == "ask_user"


def test_exhausted_only_gets_fixed_answer_and_partial_is_preserved():
    exhausted = {"status": "error", "error": {"code": "RETRY_TOOL", "recovery_class": "RETRY_TOOL", "retryable": True, "attempt": 4, "max_attempts": 4}}
    assert exhausted_response(exhausted)["answer"] == EXHAUSTED_ANSWER
    initial = {"status": "error", "error": {"code": "RETRY_TOOL", "retryable": True, "attempt": 1, "max_attempts": 4}}
    assert "answer" not in exhausted_response(initial)
    partial = {**exhausted, "status": "partial", "answer": "이미 받은 답변"}
    assert exhausted_response(partial)["answer"] == "이미 받은 답변"


def test_recovery_preserves_safe_legacy_detail_fields():
    value = error("REPAIR_INPUT")
    value["error"]["details"] = {"legacy_code": "old-format", "internal_id": "id-7", "token": "must-not-leak"}
    details = normalized_details(value["error"])
    assert details["legacy_code"] == "old-format"
    assert details["internal_id"] == "id-7"
    assert "token" not in details


def test_ambiguity_fields_reach_question_json_and_trace():
    import json
    result = error("ASK_USER")
    result["error"]["details"] = {"ambiguities": ["skillSet", "config.enemyIsBoss"]}
    result["trace"] = [{"run_id": "run-1"}]
    messages_seen = []
    class Model:
        def chat(self, messages):
            messages_seen.extend(messages)
            return json.dumps({"question": "skillSet와 config.enemyIsBoss를 알려주세요.", "ambiguous_fields": [], "missing_fields": []}, ensure_ascii=False)
    recovered = recover_response(result, Model())
    fields = ["skillSet", "config.enemyIsBoss"]
    assert json.loads(messages_seen[1]["content"])["error"]["context"]["ambiguous_fields"] == fields
    assert recovered["clarification"]["ambiguous_fields"] == fields
    assert recovered["clarification"]["question"] == recovered["answer"]
    assert recovered["error"]["details"]["ambiguous_fields"] == fields
    assert recovered["trace"][-1]["error_details"]["ambiguous_fields"] == fields


def test_streaming_clarification_emits_question_and_keeps_fields():
    import json
    result = error("ASK_USER")
    result["error"]["details"] = {"ambiguities": ["skillSet"]}
    class Model:
        def stream_chat(self, messages):
            value = json.dumps({"question": "skillSet를 알려주세요.", "ambiguous_fields": ["skillSet"], "missing_fields": []}, ensure_ascii=False)
            yield value[:10]
            yield value[10:]
    chunks = []
    recovered = recover_response(result, Model(), on_token=chunks.append)
    assert ''.join(chunks) == recovered["answer"]
    assert recovered["clarification"]["ambiguous_fields"] == ["skillSet"]
