"""Safe, bounded recovery responses for user-facing text mode."""

import json
import uuid
from datetime import datetime, timezone


SAFE_CONTEXT = ("reason", "missing_fields", "invalid_fields", "candidates", "current_context", "expected_format", "next_action")
DETAIL_FIELDS = (*SAFE_CONTEXT, "examples")
SENSITIVE = {"api_key", "apikey", "authorization", "token", "secret", "rawxml", "xml", "prompt", "notes", "itemtext", "freetext", "password"}


def _safe_value(value, depth=0):
    if depth > 3:
        return {"type": type(value).__name__}
    if isinstance(value, str):
        return value[:256]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, list):
        return [_safe_value(item, depth + 1) for item in value[:16]]
    if isinstance(value, dict):
        return {str(key): _safe_value(item, depth + 1) for key, item in list(value.items())[:32] if str(key).casefold() not in SENSITIVE}
    return {"type": type(value).__name__}


def _display_candidates(value):
    if not isinstance(value, list):
        return []
    names = []
    for item in value[:16]:
        if isinstance(item, str):
            names.append(item[:128])
        elif isinstance(item, dict):
            for key in ("display", "label", "name", "korean", "english"):
                if isinstance(item.get(key), str):
                    names.append(item[key][:128])
                    break
    return names


def normalized_details(error):
    """Normalize legacy details without exposing internal/free-form payloads."""
    raw = error.get("details") if isinstance(error, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    # Preserve non-standard legacy fields in a bounded, redacted form so
    # callers that already consume them do not lose information.
    result = {
        str(key): _safe_value(value)
        for key, value in list(raw.items())[:32]
        if key not in DETAIL_FIELDS and str(key).casefold() not in SENSITIVE
    }
    for key in DETAIL_FIELDS:
        if key not in raw:
            continue
        if key == "candidates":
            result[key] = _display_candidates(raw[key])
        else:
            result[key] = _safe_value(raw[key])
    if "next_action" not in result and isinstance(error, dict) and isinstance(error.get("next_action"), str):
        result["next_action"] = error["next_action"][:128]
    return result


def safe_context(error):
    details = normalized_details(error)
    return {key: details[key] for key in SAFE_CONTEXT if key in details}


def _template(error):
    code = error.get("code", "UNKNOWN")
    action = error.get("next_action", "human_review")
    context = safe_context(error)
    missing = context.get("missing_fields") or []
    invalid = context.get("invalid_fields") or []
    examples = context.get("examples") or []
    field_hint = (f"필수 정보: {', '.join(map(str, missing))}. " if missing else "") + (f"잘못된 입력: {', '.join(map(str, invalid))}. " if invalid else "")
    example_hint = f"예: {', '.join(map(str, examples))}." if examples else ""
    if error.get("recovery_class") == "ASK_USER":
        candidates = context.get("candidates") or []
        candidate_hint = f" 후보: {', '.join(candidates)}." if candidates else ""
        return f"추가 정보가 필요합니다. {field_hint}{context.get('reason', '질문의 대상을 더 구체적으로 알려주세요.')}{candidate_hint}"
    if error.get("recovery_class") == "REPAIR_INPUT":
        return f"입력 형식을 수정해 주세요({code}). {field_hint}{context.get('expected_format', '필요한 인자와 형식을 확인해 주세요.')} {example_hint}".strip()
    if error.get("recovery_class") == "REFRESH_CONTEXT":
        return f"최신 PoB 상태를 다시 읽어야 합니다({code}). 다음 조치: {action}."
    if error.get("recovery_class") in {"HUMAN_REVIEW", "FATAL_INTERNAL"}:
        return f"요청을 완료하지 못했습니다. 추측하지 않으며 다음 조치: {action}."
    return f"요청을 처리하지 못했습니다. 다음 조치: {action}."


def recover_response(result, model=None, *, on_token=None):
    """Return a user-facing answer while retaining the original error envelope."""
    if not isinstance(result, dict) or not isinstance(result.get("error"), dict) or result.get("answer"):
        return result
    error = result["error"]
    # ASK_USER must remain one deterministic sentence; it must not be guessed by an LLM.
    if error.get("recovery_class") == "ASK_USER" or model is None:
        answer = _template(error)
        if on_token:
            on_token(answer)
    else:
        prompt = json.dumps({"error": {"code": error.get("code"), "recovery_class": error.get("recovery_class"), "context": safe_context(error)}}, ensure_ascii=False)
        messages = [{"role": "system", "content": "Write one concise Korean recovery instruction. Do not invent facts."}, {"role": "user", "content": prompt}]
        try:
            if on_token and hasattr(model, "stream_chat"):
                chunks = []
                for chunk in model.stream_chat(messages):
                    chunks.append(chunk)
                    on_token(chunk)
                answer = "".join(chunks)
            else:
                answer = model.chat(messages)
            if not isinstance(answer, str) or not answer.strip():
                answer = _template(error)
        except Exception:
            answer = _template(error)
    updated_error = {**error, "details": normalized_details(error)}
    updated = {**result, "error": updated_error, "answer": answer}
    if isinstance(result.get("trace"), list):
        previous = result["trace"][-1] if result["trace"] and isinstance(result["trace"][-1], dict) else {}
        updated["trace"] = [*result["trace"], {"schema_version": "1.0", "event_id": "evt-" + uuid.uuid4().hex, "run_id": previous.get("run_id"), "request_id": previous.get("request_id"), "event": "recovery_response", "stage": "recovery_response", "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "duration_ms": None, "status": "completed", "attempt": 1, "max_attempts": 1, "provider": previous.get("provider", {"mode": None, "model": None, "endpoint_ref": None}), "snapshot": previous.get("snapshot", {"revision": None, "build_id": None}), "tool": None, "step_index": None, "tool_call_count": None, "retry_of": None, "plan_ref": None, "query_ref": None, "safe_args_ref": None, "error_ref": error.get("code"), "result_ref": {"facts_ref": None, "trace_ref": None, "sources_ref": None, "evidence_graph_ref": None}, "prompt_ref": None}]
    return updated
