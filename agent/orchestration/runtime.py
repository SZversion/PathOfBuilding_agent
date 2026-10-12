import hashlib
import json

from .planner import plan
from agent.pob.bridge import MAX_TOOL_ATTEMPTS, PobBridgeError, PobTimeoutError, PobUnavailableError
from agent.pob.bridge import project_snapshot, serialize_snapshot


def _bridge_error(error):
    return getattr(error, "error", {"code": "UNCLASSIFIED_FAILURE", "recovery_class": "FATAL_INTERNAL", "stage": "tool_execution", "retryable": False, "attempt": 1, "max_attempts": 1, "message": str(error), "details": {}, "next_action": "stop", "secondary_causes": [], "side_effect": "none", "operator_message": None})


def _retryable_tool_error(error):
    detail = _bridge_error(error)
    return isinstance(error, PobBridgeError) and detail.get("retryable") is True and detail.get("recovery_class") == "RETRY_TOOL"


def _set_attempt(error, attempt):
    detail = _bridge_error(error)
    detail["attempt"] = attempt
    detail["max_attempts"] = MAX_TOOL_ATTEMPTS if detail.get("retryable") else 1
    return detail


MAX_TOOL_CALLS = 8
MUTATION_TOOLS = frozenset({"replace_item", "replace_gem", "change_passive"})


def _error_envelope(code, recovery, stage, message, *, retryable=False, next_action="stop", attempt=1, max_attempts=1, details=None):
    return {"code": code, "recovery_class": recovery, "stage": stage, "retryable": retryable,
            "attempt": attempt, "max_attempts": max_attempts, "message": message,
            "details": details or {}, "next_action": next_action, "secondary_causes": [],
            "side_effect": "none", "operator_message": None}


def _budget_error(count):
    return {"code": "RETRY_EXHAUSTED", "recovery_class": "HUMAN_REVIEW", "stage": "tool_budget",
            "retryable": False, "attempt": count, "max_attempts": MAX_TOOL_CALLS,
            "message": "Tool/RAG/search call budget exhausted", "details": {"tool_call_count": count},
            "next_action": "human_review", "secondary_causes": [], "side_effect": "none",
            "operator_message": "Tool call budget requires operator review"}


def _result_uncertainty(result):
    """Never promote a bare number to authoritative evidence."""
    if not isinstance(result, dict):
        return {"status": "unverified", "reason": "missing_evidence_graph"}
    if result.get("evidenceGraph") or result.get("trace") or result.get("sources"):
        return result.get("uncertainty")
    return {"status": "unverified", "reason": "missing_evidence_graph", "message": "Tool result has no authoritative evidence graph"}


def snapshot_revision(snapshot):
    """Create the stable revision used by external-plan staleness checks."""
    if not isinstance(snapshot, dict):
        return None
    return hashlib.sha256(serialize_snapshot(snapshot).encode("utf-8")).hexdigest()


def _snapshot_diff(previous, current):
    """Return a conservative top-level diff; None means full resync is safer."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return None
    changes = {}
    for key in sorted(set(previous) | set(current)):
        before, after = previous.get(key), current.get(key)
        try:
            same = json.dumps(before, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == json.dumps(after, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            return None
        if not same:
            changes[key] = {"before": before, "after": after}
    return changes


class SnapshotSync:
    """Keep only the last normalized snapshot; never persist raw XML or credentials."""

    def __init__(self):
        self.snapshot = None
        self.revision = None

    def prepare(self, current):
        if not isinstance(current, dict):
            return {"mode": "full", "snapshot": None, "snapshotRevision": None, "baseRevision": None}
        normalized = project_snapshot(current)
        revision = snapshot_revision(normalized)
        if self.snapshot is None or self.revision is None:
            self.snapshot, self.revision = normalized, revision
            return {"mode": "full", "snapshot": normalized, "snapshotRevision": revision, "baseRevision": None}
        diff = _snapshot_diff(self.snapshot, normalized)
        base = self.revision
        self.snapshot, self.revision = normalized, revision
        if diff is None:
            return {"mode": "full", "snapshot": normalized, "snapshotRevision": revision, "baseRevision": None}
        return {"mode": "diff", "diff": {"baseRevision": base, "revision": revision, "changes": diff}, "snapshotRevision": revision, "baseRevision": base}


def execute_plan(question, planned, search=None, handlers=None, *, snapshot_revision_value=None, current_revision=None):
    """Execute a planner result without raising at the orchestration boundary."""
    handlers = handlers or {}
    output = {
        "question": question,
        "intent": planned.get("intent", "unknown") if isinstance(planned, dict) else "unknown",
        "steps": [],
        "tool_call_count": 0,
        "snapshotRevision": snapshot_revision_value,
    }
    steps = planned.get("steps", []) if isinstance(planned, dict) else []
    if not isinstance(steps, list):
        output["steps"].append({"tool": None, "status": "error", "error": _error_envelope("INPUT_INVALID", "REPAIR_INPUT", "plan_validation", "steps must be a list", next_action="repair_input")})
        return output
    budget_exhausted = False
    seen_calls = {}
    for step in steps:
        if output["tool_call_count"] >= MAX_TOOL_CALLS:
            output["steps"].append({"tool": step.get("tool") if isinstance(step, dict) else None,
                                     "status": "human_review", "error": _budget_error(output["tool_call_count"])})
            budget_exhausted = True
            break
        if not isinstance(step, dict) or not isinstance(step.get("tool"), str):
            output["steps"].append({"tool": None, "status": "error", "error": _error_envelope("INPUT_INVALID", "REPAIR_INPUT", "plan_validation", "invalid planner step", next_action="repair_input")})
            continue
        tool = step["tool"]
        if "arguments" not in step:
            output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("INPUT_INVALID", "REPAIR_INPUT", "plan_validation", "arguments are required", next_action="repair_input")})
            continue
        arguments = step["arguments"]
        if not isinstance(arguments, dict):
            output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("INPUT_INVALID", "REPAIR_INPUT", "plan_validation", "arguments must be a dict", next_action="repair_input")})
            continue
        expected_revision = step.get("expectedSnapshotRevision")
        if expected_revision is not None and (not isinstance(expected_revision, str) or not expected_revision.strip()):
            output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("INPUT_INVALID", "REPAIR_INPUT", "plan_validation", "expectedSnapshotRevision must be a non-empty string", next_action="repair_input")})
            continue
        signature = (tool, json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        revisions = seen_calls.setdefault(signature, set())
        if expected_revision in revisions:
            output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("DUPLICATE_TOOL_CALL", "REPAIR_INPUT", "plan_validation", "exact duplicate Tool call rejected", next_action="repair_input")})
            continue
        revisions.add(expected_revision)
        if expected_revision is not None and snapshot_revision_value is not None and expected_revision != snapshot_revision_value:
            output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("SNAPSHOT_REVISION_CONFLICT", "REFRESH_CONTEXT", "snapshot_validation", "planner revision is stale", next_action="recapture_snapshot", details={"expected": expected_revision, "current": snapshot_revision_value})})
            continue
        if tool == "search_knowledge":
            if search is None:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": _error_envelope("SEARCH_UNAVAILABLE", "REJECT", "knowledge_search", "knowledge search is not configured", next_action="reject_request")})
                continue
            output["tool_call_count"] += 1
            try:
                result = search.search(arguments.get("query", ""), limit=arguments.get("limit", 10), category=arguments.get("category"))
            except Exception as error:  # boundary: keep one failed step inspectable
                output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("SEARCH_ERROR", "RETRY_TOOL", "knowledge_search", str(error), retryable=True, next_action="retry_bounded", max_attempts=MAX_TOOL_ATTEMPTS)})
            else:
                step_result = {"tool": tool, "status": "ok", "result": result}
                uncertainty = _result_uncertainty(result)
                if uncertainty is not None:
                    step_result["uncertainty"] = uncertainty
                output["steps"].append(step_result)
            continue
        if tool == "resolve_item_alias":
            if search is None:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": _error_envelope("SEARCH_UNAVAILABLE", "REJECT", "knowledge_search", "knowledge search is not configured", next_action="reject_request")})
                continue
            output["tool_call_count"] += 1
            try:
                result = search.resolve_item_alias(arguments.get("query", ""), category=arguments.get("category"))
            except Exception as error:
                output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("SEARCH_ERROR", "RETRY_TOOL", "knowledge_search", str(error), retryable=True, next_action="retry_bounded", max_attempts=MAX_TOOL_ATTEMPTS)})
            else:
                output["steps"].append({"tool": tool, "status": "ok" if result else "unavailable", "result": result} if result else {"tool": tool, "status": "unavailable", "error": _error_envelope("USER_CONTEXT_MISSING", "ASK_USER", "alias_resolution", "item alias was not found", next_action="ask_user")})
            continue
        if tool == "resolve_skill_alias":
            if search is None:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": _error_envelope("SEARCH_UNAVAILABLE", "REJECT", "knowledge_search", "knowledge search is not configured", next_action="reject_request")})
                continue
            output["tool_call_count"] += 1
            try:
                result = search.resolve_skill_alias(arguments.get("query", ""))
            except Exception as error:
                output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("SEARCH_ERROR", "RETRY_TOOL", "knowledge_search", str(error), retryable=True, next_action="retry_bounded", max_attempts=MAX_TOOL_ATTEMPTS)})
            else:
                output["steps"].append({"tool": tool, "status": "ok", "result": result} if result else {"tool": tool, "status": "unavailable", "error": _error_envelope("USER_CONTEXT_MISSING", "ASK_USER", "alias_resolution", "skill alias was not found", next_action="ask_user")})
            continue
        handler = handlers.get(tool)
        if not callable(handler):
            output["steps"].append({"tool": tool, "status": "unavailable", "error": _error_envelope("HANDLER_NOT_CONFIGURED", "FATAL_INTERNAL", "tool_dispatch", "handler is not configured", next_action="report_error")})
            continue
        for attempt in range(1, MAX_TOOL_ATTEMPTS + 1):
            if output["tool_call_count"] >= MAX_TOOL_CALLS:
                output["steps"].append({"tool": tool, "status": "human_review", "error": _budget_error(output["tool_call_count"])})
                budget_exhausted = True
                break
            output["tool_call_count"] += 1
            if callable(current_revision) and expected_revision is not None:
                observed_revision = current_revision()
                if observed_revision != expected_revision:
                    output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("SNAPSHOT_REVISION_CONFLICT", "REFRESH_CONTEXT", "snapshot_validation", "PoB state changed before Tool execution", next_action="recapture_snapshot", details={"expected": expected_revision, "current": observed_revision})})
                    break
            try:
                result = handler(arguments)
            except PobUnavailableError as error:
                output["steps"].append({"tool": tool, "status": "unavailable", "error": _set_attempt(error, attempt)})
                break
            except PobTimeoutError as error:
                if tool in MUTATION_TOOLS:
                    detail = _set_attempt(error, attempt)
                    detail.update({"code": "MUTATION_TIMEOUT", "recovery_class": "REFRESH_CONTEXT", "retryable": False, "max_attempts": 1, "next_action": "recapture_snapshot", "operator_message": "Mutation outcome is uncertain; refresh the latest snapshot and verify idempotency before retrying."})
                    output["steps"].append({"tool": tool, "status": "timeout", "error": detail})
                    break
                if _retryable_tool_error(error) and attempt < MAX_TOOL_ATTEMPTS:
                    continue
                output["steps"].append({"tool": tool, "status": "timeout", "error": _set_attempt(error, attempt)})
                break
            except PobBridgeError as error:
                if tool in MUTATION_TOOLS and _retryable_tool_error(error):
                    detail = _set_attempt(error, attempt)
                    detail.update({"code": "MUTATION_UNCERTAIN", "recovery_class": "REFRESH_CONTEXT", "retryable": False, "max_attempts": 1, "next_action": "recapture_snapshot", "operator_message": "Mutation outcome is uncertain; refresh the latest snapshot and verify idempotency before retrying."})
                    output["steps"].append({"tool": tool, "status": "error", "error": detail})
                    break
                if _retryable_tool_error(error) and attempt < MAX_TOOL_ATTEMPTS:
                    continue
                output["steps"].append({"tool": tool, "status": "error", "error": _set_attempt(error, attempt)})
                break
            except Exception as error:  # boundary: tool failures belong to the step
                output["steps"].append({"tool": tool, "status": "error", "error": _error_envelope("TOOL_EXECUTION_ERROR", "FATAL_INTERNAL", "tool_execution", str(error), next_action="report_error")})
                break
            else:
                step_result = {"tool": tool, "status": "ok", "result": result}
                uncertainty = _result_uncertainty(result)
                if uncertainty is not None:
                    step_result["uncertainty"] = uncertainty
                output["steps"].append(step_result)
                break
        if budget_exhausted:
            break
    return output


execute = execute_plan


def run_question(question, search=None, handlers=None, *, snapshot=None, current_revision=None):
    """Plan and execute one question."""
    planned = plan(question)
    prepared_revision = snapshot_revision(snapshot) if snapshot is not None else None
    return execute_plan(question, planned, search=search, handlers=handlers,
                        snapshot_revision_value=prepared_revision,
                        current_revision=current_revision)
