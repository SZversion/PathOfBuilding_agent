import json

from .runtime import SnapshotSync, execute_plan
from .trace import TraceRecorder


ALLOWED_TOOLS = frozenset({
    "search_knowledge", "resolve_item_alias", "resolve_skill_alias", "get_projectile_count", "get_curse_limit", "get_elemental_penetration",
    "get_socket_order", "get_skill_chain", "compare_support_effect", "explain_damage_change", "compare_build_states", "replace_item", "replace_gem", "change_passive",
    "get_skill_dps", "get_highest_dps_skill", "get_skill_breakdown", "get_item_modifiers",
    "get_character_stats", "get_skill_stats",
    "get_projectile_behavior", "get_trigger_sequence", "get_curse_application_order", "get_ailment_effect",
    "get_damage_breakdown", "get_conversion_chain", "get_effective_resistance", "get_support_links",
    "resolve_skill_context",
    "get_duration", "explain_stat",
})
TOOL_ALIASES = {tool.replace("_", ""): tool for tool in ALLOWED_TOOLS}
TOOL_ALIASES.update({"getCurseLimit": "get_curse_limit", "getProjectileCount": "get_projectile_count", "getElementalPenetration": "get_elemental_penetration", "searchKnowledge": "search_knowledge", "getSocketOrder": "get_socket_order", "getSkillChain": "get_skill_chain", "compareSupportEffect": "compare_support_effect", "explainDamageChange": "explain_damage_change"})
MAX_STEPS = 8
MAX_PLANNER_ATTEMPTS = 5
MUTATION_TOOLS = frozenset({"replace_item", "replace_gem", "change_passive"})
READ_ONLY_TOOLS = frozenset(ALLOWED_TOOLS - MUTATION_TOOLS)
PLAN_FIELDS = frozenset({"schema_version", "intent", "operation", "evidenceLevel", "required_evidence", "stop_condition", "ambiguities", "steps", "metadata"})
STEP_FIELDS = frozenset({"tool", "arguments", "expectedSnapshotRevision"})
QUERY_FIELDS = frozenset({"schema_version", "text", "intent", "operation", "evidenceLevel", "required_evidence", "stop_condition", "subject", "context", "ambiguities", "confidence", "requires"})
INTENT_ENUM = frozenset({"unknown", "stat", "pob_stat", "skill_stat", "item_stat", "mechanism", "damage", "projectile", "chain", "duration", "curse", "resistance", "compare", "build_comparison", "search", "change"})
OPERATION_ENUM = frozenset({"answer", "read", "explain", "compare", "change", "search"})
EVIDENCE_LEVEL_ENUM = frozenset({"authoritative", "calculated", "mixed", "knowledge", "external", "any"})
INTENT_REQUIREMENTS = {
    "projectile": {"tools": {"get_projectile_count"}, "evidence": {"calculated"}},
    "chain": {"tools": {"get_skill_chain"}, "evidence": {"calculated"}},
    "duration": {"tools": {"get_duration"}, "evidence": {"calculated"}},
    "damage": {"tools": {"get_skill_dps", "get_damage_breakdown"}, "evidence": {"calculated", "authoritative"}},
    "mechanism": {"tools": {"resolve_skill_context", "get_skill_breakdown"}, "evidence": {"calculated", "knowledge"}},
    "compare": {"tools": {"compare_build_states"}, "evidence": {"calculated"}},
    "build_comparison": {"tools": {"compare_build_states"}, "evidence": {"calculated"}},
}
ARGUMENT_TYPES = {
    "query": str, "category": str, "skillName": str, "supportName": str,
    "stat": str, "skillSetSelector": str, "itemSetSelector": str,
    "buildId": str, "skillIndex": int, "socketGroup": (int, str),
    "gemIdentity": str, "level": int, "quality": int, "enabled": bool,
    "limit": int, "nodeId": int, "operation": str, "slot": str,
    "itemIdentity": str, "itemText": str, "condition": dict,
    "config": dict, "beforeState": (dict, str), "afterState": (dict, str),
    "comparisonFields": list,
}
REQUIRED_ARGUMENTS = {"search_knowledge": ("query",), "resolve_item_alias": ("query",), "resolve_skill_alias": ("query",)}
SKILL_AWARE_READ_ONLY_TOOLS = frozenset({
    "get_skill_dps", "get_skill_stats", "get_skill_breakdown", "get_projectile_count",
    "get_projectile_behavior", "get_trigger_sequence", "get_curse_application_order",
    "get_ailment_effect", "get_damage_breakdown", "get_conversion_chain",
    "get_effective_resistance", "get_elemental_penetration", "get_support_links",
    "resolve_skill_context", "get_skill_chain", "get_socket_order", "get_duration",
    "explain_stat", "compare_support_effect", "explain_damage_change",
})

TOOL_MIN_ARGUMENTS = {tool: {} for tool in READ_ONLY_TOOLS}
for _tool in REQUIRED_ARGUMENTS:
    TOOL_MIN_ARGUMENTS[_tool] = {"required": list(REQUIRED_ARGUMENTS[_tool]), "types": {key: "string" for key in REQUIRED_ARGUMENTS[_tool]}}
TOOL_MIN_ARGUMENTS["compare_build_states"] = {"required": ["beforeState", "afterState"], "types": {"beforeState": "object|string", "afterState": "object|string"}}

_PLANNER_CATALOG = json.dumps(
    {tool: TOOL_MIN_ARGUMENTS[tool] for tool in sorted(READ_ONLY_TOOLS)},
    ensure_ascii=False, sort_keys=True, separators=(",", ":"),
)
PLANNER_SYSTEM = f"""You are a PoE Path of Building read-only tool planner. Return JSON only with schema_version, intent, operation, evidenceLevel, required_evidence, stop_condition, and steps. Each step has tool, arguments, and expectedSnapshotRevision. Use ONLY canonical Tool names and this registry: {_PLANNER_CATALOG}. Never invent, translate, or paraphrase Tool names. Never return mutation Tools, free-text commands, raw XML, or PoB numbers. Example: {{\"tool\":\"get_curse_limit\",\"arguments\":{{}}}}. If the query is ambiguous, return intent=unknown and stop_condition={{\"type\":\"ask_user\"}}."""
ANSWER_SYSTEM = """Answer the user's PoE question using only the supplied Tool results and knowledge documents. By default, answer in Korean using friendly and clear wording. Distinguish calculated values, applied effects, and calculation evidence. If a result is unavailable or an input is ambiguous, state that plainly and do not guess. Answer Korean questions in Korean."""
ENVELOPE_FIELDS = frozenset({"status", "version", "snapshotRevision", "side_effect", "operator_message", "facts", "conditions", "trace", "sources", "evidenceGraph", "uncertainty", "error"})


def _json_object(text):
    if not isinstance(text, str):
        raise ValueError("model plan must be text")
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model plan is not JSON")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("model plan must be an object")
    return value


def _model_safe_execution(execution):
    """Strip handler-specific fields before returning Tool results to the model."""
    safe = {key: execution.get(key) for key in ("snapshotRevision", "tool_call_count") if key in execution}
    safe["steps"] = []
    for step in execution.get("steps", []):
        projected = {key: step[key] for key in ("tool", "status", "uncertainty") if key in step}
        if isinstance(step.get("error"), dict):
            projected["error"] = {key: step["error"].get(key) for key in ENVELOPE_FIELDS if key in step["error"]}
        if isinstance(step.get("result"), dict):
            projected["result"] = {key: step["result"].get(key) for key in ENVELOPE_FIELDS if key in step["result"]}
        elif "result" in step:
            projected["result"] = step["result"]
        safe["steps"].append(projected)
    return safe


def _repair_feedback(error):
    """Build bounded planner feedback without echoing the failed plan/prompt."""
    code = getattr(error, "code", None) or "MODEL_SCHEMA_INVALID"
    details = getattr(error, "details", {})
    safe_details = {}
    if isinstance(details, dict):
        for key in ("fields", "argument", "arguments", "tool", "expected", "actual"):
            value = details.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                safe_details[key] = value
            elif isinstance(value, list):
                safe_details[key] = [item for item in value[:8] if isinstance(item, (str, int, float, bool))]
    return {
        "code": code,
        "message": str(error)[:240] if isinstance(error, PlanValidationError) else "planner response failed the JSON/schema contract",
        "details": safe_details,
        "instruction": "Return a new plan using only canonical Tool names, object arguments, and the declared argument schema. Do not repeat the invalid field.",
    }


class PlanValidationError(ValueError):
    """A planner contract error that can cross the orchestration boundary."""

    def __init__(self, message, code="INPUT_INVALID", details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _canonical_arguments(arguments):
    return json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_arguments(tool, arguments):
    if not isinstance(arguments, dict):
        raise PlanValidationError("tool arguments must be an object")
    if any(not isinstance(key, str) for key in arguments):
        raise PlanValidationError("tool argument keys must be strings")
    forbidden = {"command", "freeText", "prompt", "rawXml"} & set(arguments)
    if forbidden:
        raise PlanValidationError("free-text or raw PoB input is not allowed", details={"fields": sorted(forbidden)})
    unknown = set(arguments) - set(ARGUMENT_TYPES)
    if unknown:
        raise PlanValidationError("unsupported tool arguments", details={"fields": sorted(unknown)})
    for key, value in arguments.items():
        expected = ARGUMENT_TYPES.get(key)
        if expected is not None:
            if isinstance(value, bool) and expected is int:
                raise PlanValidationError("argument has invalid type", details={"argument": key, "expected": "integer"})
            if not isinstance(value, expected):
                raise PlanValidationError("argument has invalid type", details={"argument": key, "expected": str(expected)})
    for key in REQUIRED_ARGUMENTS.get(tool, ()):
        if not isinstance(arguments.get(key), str) or not arguments[key].strip():
            raise PlanValidationError("required argument is missing or invalid", details={"argument": key})


def _normalize_skill_argument(tool, arguments):
    """Accept the common shorthand only for Tools that actually resolve skills."""
    if not isinstance(arguments, dict) or "skill" not in arguments:
        return arguments
    if tool not in SKILL_AWARE_READ_ONLY_TOOLS:
        raise PlanValidationError("skill is not compatible with this Tool", details={"tool": tool, "argument": "skill"})
    normalized = dict(arguments)
    shorthand = normalized.pop("skill")
    if "skillName" in normalized:
        if not isinstance(shorthand, str) or not isinstance(normalized["skillName"], str):
            raise PlanValidationError("skill and skillName must be strings", details={"arguments": ["skill", "skillName"]})
        if shorthand.strip().casefold() != normalized["skillName"].strip().casefold():
            raise PlanValidationError("skill and skillName conflict", details={"arguments": ["skill", "skillName"]})
    else:
        normalized["skillName"] = shorthand
    return normalized


def normalize_query(value):
    """Normalize the public query shape while accepting the legacy string form."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise PlanValidationError("query.text is required")
        return {"schema_version": "1.0", "text": text, "intent": "unknown", "operation": "answer", "evidenceLevel": "authoritative", "required_evidence": [], "stop_condition": {}, "subject": None, "context": {}, "ambiguities": [], "confidence": None, "requires": []}
    if not isinstance(value, dict):
        raise PlanValidationError("query must be a string or object")
    unknown = set(value) - QUERY_FIELDS - {"question"}
    if unknown:
        raise PlanValidationError("unsupported query fields", details={"fields": sorted(unknown)})
    text = value.get("text", value.get("question"))
    if not isinstance(text, str) or not text.strip():
        raise PlanValidationError("query.text is required")
    result = dict(value)
    result.pop("question", None)
    result["schema_version"] = str(result.get("schema_version", "1.0"))
    result["text"] = text.strip()
    result["intent"] = result.get("intent", "unknown")
    result["operation"] = result.get("operation", "answer")
    result["evidenceLevel"] = result.get("evidenceLevel", "authoritative")
    result["required_evidence"] = result.get("required_evidence", [])
    result["stop_condition"] = result.get("stop_condition", {})
    result["subject"] = result.get("subject")
    result["context"] = result.get("context", {})
    result["ambiguities"] = result.get("ambiguities", [])
    result["confidence"] = result.get("confidence")
    result["requires"] = result.get("requires", [])
    if result["schema_version"] != "1.0" or result["intent"] not in INTENT_ENUM or result["operation"] not in OPERATION_ENUM or result["evidenceLevel"] not in EVIDENCE_LEVEL_ENUM:
        raise PlanValidationError("query enum or schema_version is invalid")
    if not isinstance(result["required_evidence"], list) or any(not isinstance(item, str) for item in result["required_evidence"]):
        raise PlanValidationError("query.required_evidence must be a string array")
    if not isinstance(result["stop_condition"], (dict, str)):
        raise PlanValidationError("query.stop_condition must be an object or string")
    if result["subject"] is not None and not isinstance(result["subject"], (str, dict)):
        raise PlanValidationError("query.subject must be a string or object")
    if not isinstance(result["context"], dict) or not isinstance(result["ambiguities"], list) or not isinstance(result["requires"], list):
        raise PlanValidationError("query.context, ambiguities, and requires have invalid types")
    if len(result["ambiguities"]) > 16 or len(result["requires"]) > 32:
        raise PlanValidationError("query context arrays are too large")
    if result["confidence"] is not None and (isinstance(result["confidence"], bool) or not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1):
        raise PlanValidationError("query.confidence must be between 0 and 1")
    return result


def _validate_completeness(plan, *, enforce_evidence=False):
    requirement = INTENT_REQUIREMENTS.get(plan.get("intent"))
    if not requirement:
        return
    tools = {step.get("tool") for step in plan.get("steps", [])}
    missing_tools = sorted(requirement["tools"] - tools)
    declared = set(plan.get("required_evidence", []))
    missing_evidence = ["required_evidence"] if enforce_evidence and plan.get("intent") in {"mechanism", "damage", "compare"} and not declared else []
    if missing_tools or missing_evidence:
        raise PlanValidationError("plan is incomplete for its intent", code="PLAN_INCOMPLETE", details={"missing_tools": missing_tools, "missing_evidence": missing_evidence})


def validate_plan(value):
    if not isinstance(value, dict) or not isinstance(value.get("steps"), list):
        raise PlanValidationError("plan.steps must be a list")
    legacy = "schema_version" not in value
    if "schema_version" in value and value["schema_version"] != "1.0":
        raise PlanValidationError("unsupported plan schema_version")
    if "intent" in value and not isinstance(value["intent"], str):
        raise PlanValidationError("plan.intent must be a string")
    if "intent" in value and not legacy and value["intent"] not in INTENT_ENUM:
        raise PlanValidationError("plan.intent is not a supported enum")
    if "metadata" in value and not isinstance(value["metadata"], dict):
        raise PlanValidationError("plan.metadata must be an object")
    unknown_plan_fields = set(value) - PLAN_FIELDS
    if unknown_plan_fields:
        raise PlanValidationError("unsupported plan fields", details={"fields": sorted(unknown_plan_fields)})
    value.setdefault("schema_version", "1.0")
    value.setdefault("intent", "unknown")
    value.setdefault("operation", "answer")
    value.setdefault("evidenceLevel", "authoritative")
    value.setdefault("required_evidence", [])
    value.setdefault("stop_condition", {})
    value.setdefault("ambiguities", [])
    if not legacy and (value["intent"] == "unknown" or value["ambiguities"] or (isinstance(value["stop_condition"], dict) and value["stop_condition"].get("type") == "ask_user")):
        raise PlanValidationError("planner requires user clarification", code="AMBIGUOUS_ALIAS")
    if value["operation"] not in OPERATION_ENUM or value["evidenceLevel"] not in EVIDENCE_LEVEL_ENUM:
        raise PlanValidationError("plan operation or evidenceLevel is not a supported enum")
    if not isinstance(value["required_evidence"], list) or any(not isinstance(item, str) for item in value["required_evidence"]):
        raise PlanValidationError("plan.required_evidence must be a string array")
    if not isinstance(value["ambiguities"], list) or len(value["ambiguities"]) > 16:
        raise PlanValidationError("plan.ambiguities must be a bounded array")
    if not isinstance(value["stop_condition"], (dict, str)):
        raise PlanValidationError("plan.stop_condition must be an object or string")
    steps = value["steps"]
    if len(steps) > MAX_STEPS:
        raise PlanValidationError("plan has too many steps", code="RETRY_EXHAUSTED")
    seen = {}
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("tool"), str):
            raise PlanValidationError("each step needs a tool")
        unknown_step_fields = set(step) - STEP_FIELDS
        if unknown_step_fields:
            raise PlanValidationError("unsupported step fields", details={"fields": sorted(unknown_step_fields)})
        tool = TOOL_ALIASES.get(step["tool"], step["tool"])
        step["tool"] = tool
        if tool not in ALLOWED_TOOLS:
            raise PlanValidationError("tool is not allowed: " + tool, code="TOOL_NOT_FOUND")
        if tool in MUTATION_TOOLS:
            raise PlanValidationError("mutation tools are disabled in read-only orchestration", code="MUTATION_NOT_PERSISTENT")
        step["arguments"] = _normalize_skill_argument(tool, step.get("arguments"))
        _validate_arguments(tool, step["arguments"])
        revision = step.get("expectedSnapshotRevision")
        if revision is not None and (not isinstance(revision, str) or not revision.strip()):
            raise PlanValidationError("expectedSnapshotRevision must be a non-empty string or null")
        signature = (tool, _canonical_arguments(step["arguments"]))
        revisions = seen.setdefault(signature, set())
        if revision in revisions:
            raise PlanValidationError("exact duplicate tool call", code="DUPLICATE_TOOL_CALL")
        revisions.add(revision)
    if not legacy:
        _validate_completeness(value, enforce_evidence=True)
    return value


class AgentLoop:
    def __init__(self, model, *, snapshot_provider=None, trace_factory=TraceRecorder, trace_exporter=None):
        if not hasattr(model, "chat"):
            raise TypeError("model must provide chat(messages)")
        self.model = model
        self.snapshot_provider = snapshot_provider
        self.snapshot_sync = SnapshotSync()
        self.trace_factory = trace_factory
        if trace_exporter is None:
            from .langfuse_exporter import LangfuseExporter
            trace_exporter = LangfuseExporter.from_env()
        self.trace_exporter = trace_exporter

    def _chat(self, messages, *, attempts=2, recorder=None, stream=False, on_token=None):
        last = None
        for attempt in range(1, attempts + 1):
            started = __import__("time").monotonic()
            provider = recorder.provider_metadata(self.model) if recorder else None
            if recorder:
                recorder.emit("provider_started", "provider", "started", attempt=attempt, provider=provider, prompt_ref=recorder.prompt_ref(messages))
            try:
                if stream and hasattr(self.model, "stream_chat"):
                    chunks = []
                    try:
                        for chunk in self.model.stream_chat(messages):
                            chunks.append(chunk)
                            if on_token:
                                on_token(chunk)
                    except Exception as stream_error:
                        stream_error._partial_text = "".join(chunks)
                        raise
                    result = "".join(chunks)
                else:
                    result = self.model.chat(messages)
                if recorder:
                    recorder.emit("provider_completed", "provider", "ok", attempt=attempt, provider=provider, prompt_ref=recorder.prompt_ref(messages), duration_ms=round((__import__("time").monotonic() - started) * 1000))
                return result
            except Exception as error:
                last = error
                if recorder:
                    detail = getattr(error, "error", {})
                    timeout = detail.get("code") == "TIMEOUT" or detail.get("details", {}).get("timeout") is True or isinstance(error, TimeoutError)
                    recorder.emit("provider_failed", "provider", "timeout" if timeout else "failed", attempt=attempt, provider=provider, prompt_ref=recorder.prompt_ref(messages), error_ref="TIMEOUT" if timeout else detail.get("code", type(error).__name__), duration_ms=round((__import__("time").monotonic() - started) * 1000))
                detail = getattr(error, "error", {})
                if isinstance(error, TimeoutError):
                    detail = {"retryable": True}
                if detail.get("retryable") is not True or attempt >= attempts:
                    raise
        raise last

    def run(self, question, search=None, handlers=None, *, snapshot=None, current_revision=None, request_id=None, on_token=None):
        recorder = self.trace_factory(request_id=request_id, exporter=self.trace_exporter)
        recorder.emit("run_started", "run", "started", provider=recorder.provider_metadata(self.model))
        try:
            query = normalize_query(question)
        except PlanValidationError as error:
            recorder.emit("run_completed", "run", "rejected", error_ref="INPUT_INVALID")
            return {"status": "plan_error", "error": {"code": "INPUT_INVALID", "message": str(error), "next_action": "repair_input"}, "trace": recorder.events}
        question_text = query["text"]
        recorder.emit("planner_started", "planner", "started", attempt=1, max_attempts=MAX_PLANNER_ATTEMPTS, query_ref=recorder.query_ref(query), provider=recorder.provider_metadata(self.model))
        if snapshot is None and callable(self.snapshot_provider):
            snapshot = self.snapshot_provider()
        sync = self.snapshot_sync.prepare(snapshot) if snapshot is not None else None
        planning_payload = {"question": question_text, "query": query}
        if sync is not None:
            planning_payload["context"] = sync
            recorder.set_snapshot((sync or {}).get("snapshotRevision"), snapshot.get("buildId") if isinstance(snapshot, dict) else None)
        last_error = None
        repair_feedback = None
        for llm_attempt in range(1, MAX_PLANNER_ATTEMPTS + 1):
            try:
                planner_input = dict(planning_payload)
                if repair_feedback is not None:
                    planner_input["repair_feedback"] = repair_feedback
                planned = validate_plan(_json_object(self._chat([
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": json.dumps(planner_input, ensure_ascii=False)},
                ], recorder=recorder)))
                recorder.emit("planner_completed", "planner", "ok", attempt=llm_attempt, max_attempts=MAX_PLANNER_ATTEMPTS, query_ref=recorder.query_ref(query), plan_ref=recorder.plan_ref(planned))
                break
            except PlanValidationError as error:
                repair_feedback = _repair_feedback(error)
                recorder.emit("planner_failed", "planner", "rejected", attempt=llm_attempt, max_attempts=MAX_PLANNER_ATTEMPTS, error_ref=error.code)
                if error.code == "AMBIGUOUS_ALIAS":
                    recorder.emit("run_completed", "run", "rejected", error_ref=error.code)
                    return {"status": "error", "error": {"code": error.code, "recovery_class": "ASK_USER", "stage": "plan_validation", "retryable": False, "attempt": llm_attempt, "max_attempts": llm_attempt, "message": str(error), "details": error.details, "next_action": "ask_user", "side_effect": "none", "operator_message": None, "secondary_causes": []}, "trace": recorder.events}
                if llm_attempt < MAX_PLANNER_ATTEMPTS:
                    continue
                recorder.emit("run_completed", "run", "rejected", error_ref="REPAIR_INPUT")
                return {"status": "error", "error": {"code": "REPAIR_INPUT", "recovery_class": "REPAIR_INPUT", "stage": "plan_validation", "retryable": False, "attempt": llm_attempt, "max_attempts": MAX_PLANNER_ATTEMPTS, "message": "planner failed after bounded repair attempts", "details": repair_feedback, "next_action": "human_review", "side_effect": "none", "operator_message": None, "secondary_causes": []}, "trace": recorder.events}
            except Exception as error:
                last_error = error
                repair_feedback = _repair_feedback(error)
                recorder.emit("planner_failed", "planner", "failed", attempt=llm_attempt, max_attempts=MAX_PLANNER_ATTEMPTS, error_ref=getattr(error, "error", {}).get("code", type(error).__name__))
                if llm_attempt == MAX_PLANNER_ATTEMPTS:
                    detail = {"code": "REPAIR_INPUT", "recovery_class": "REPAIR_INPUT", "stage": "plan_validation", "retryable": False, "attempt": llm_attempt, "max_attempts": MAX_PLANNER_ATTEMPTS, "message": "planner failed after bounded repair attempts", "details": repair_feedback, "next_action": "human_review", "side_effect": "none", "operator_message": None, "secondary_causes": []}
                    detail = dict(detail)
                    recorder.emit("run_completed", "run", "rejected", error_ref=detail.get("code"))
                    return {"status": "plan_error", "error": detail, "trace": recorder.events}
        if last_error is not None and "planned" not in locals():
            recorder.emit("run_completed", "run", "rejected", error_ref="REPAIR_INPUT")
            return {"status": "plan_error", "error": {"code": "REPAIR_INPUT", "recovery_class": "REPAIR_INPUT", "stage": "plan_validation", "retryable": False, "attempt": MAX_PLANNER_ATTEMPTS, "max_attempts": MAX_PLANNER_ATTEMPTS, "message": "planner failed after bounded repair attempts", "details": repair_feedback or {}, "next_action": "human_review", "side_effect": "none", "operator_message": None, "secondary_causes": []}, "trace": recorder.events}
        execution = execute_plan(question_text, planned, search=search, handlers=handlers,
                                 snapshot_revision_value=(sync or {}).get("snapshotRevision"),
                                 current_revision=current_revision)
        for index, step in enumerate(execution.get("steps", [])):
            final_attempt = step.get("attempt") or (step.get("error") or {}).get("attempt", 1)
            final_count = step.get("tool_call_count", execution.get("tool_call_count"))
            safe_args = recorder.safe_args_ref(planned.get("steps", [])[index].get("arguments", {}) if index < len(planned.get("steps", [])) else {})
            for attempt in range(1, final_attempt + 1):
                count = max(1, final_count - final_attempt + attempt) if isinstance(final_count, int) else final_count
                retry_of = f"tool:{index}:attempt:{attempt - 1}" if attempt > 1 else None
                recorder.emit("tool_started", "tool", "started", attempt=attempt, retry_of=retry_of, step_index=index, tool=step.get("tool"), tool_call_count=count, plan_ref=recorder.plan_ref(planned), safe_args_ref=safe_args)
                if attempt < final_attempt:
                    recorder.emit("tool_failed", "tool", "failed", attempt=attempt, retry_of=retry_of, step_index=index, tool=step.get("tool"), tool_call_count=count, error_ref="RETRY_TOOL")
                elif step.get("status") == "ok":
                    recorder.emit("tool_completed", "tool", "ok", attempt=attempt, retry_of=retry_of, step_index=index, tool=step.get("tool"), tool_call_count=count, result_ref=recorder.result_refs(step.get("result")))
                else:
                    status = "timeout" if step.get("status") == "timeout" or (step.get("error") or {}).get("code") == "TIMEOUT" else step.get("status", "failed")
                    recorder.emit("tool_failed", "tool", status, attempt=attempt, retry_of=retry_of, step_index=index, tool=step.get("tool"), tool_call_count=count, error_ref=(step.get("error") or {}).get("code"))
        evidence_failure = next((
            {"code": "EVIDENCE_INCOMPLETE", "next_action": "reject_request", "message": "required authoritative evidence is missing"}
            for step in execution.get("steps", [])
            if step.get("status") == "ok" and isinstance(step.get("uncertainty"), dict)
            and step["uncertainty"].get("reason") == "missing_evidence_graph"
            and planned.get("required_evidence")
        ), None)
        authoritative_failure = next((step.get("error") for step in execution.get("steps", [])
                                      if isinstance(step.get("error"), dict) and step["error"].get("code") in {
                                          "POB_CALCULATION_ERROR", "VALUE_UNAVAILABLE", "USER_CONTEXT_MISSING",
                                          "AMBIGUOUS_ALIAS", "SNAPSHOT_REVISION_CONFLICT",
                                      }), None) or evidence_failure
        if authoritative_failure:
            recorder.emit("final_started", "final", "started", plan_ref=recorder.plan_ref(planned))
            code = authoritative_failure.get("code")
            next_action = authoritative_failure.get("next_action", "reject_request")
            answer = f"PoB에서 값을 가져오지 못했습니다 ({code}). 다음 조치: {next_action}. 근거가 부족하므로 추측하지 않습니다."
            uncertainty = {"code": code, "reason": "authoritative PoB result unavailable", "next_action": next_action}
            recorder.emit("final_completed", "final", "partial", result_ref=recorder.result_refs({"uncertainty": uncertainty}))
            recorder.emit("run_completed", "run", "partial", error_ref=code)
            return {"status": "partial", "plan": planned, "execution": execution, "answer": answer, "uncertainty": uncertainty, "trace": recorder.events}
        recorder.emit("final_started", "final", "started", plan_ref=recorder.plan_ref(planned))
        answer_payload = {"question": question_text, "results": _model_safe_execution(execution)}
        try:
            answer = self._chat([
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps(answer_payload, ensure_ascii=False)},
            ], recorder=recorder, stream=True, attempts=1, on_token=on_token)
        except Exception as error:
            detail = getattr(error, "error", None) or {"code": "RETRY_LLM", "recovery_class": "RETRY_LLM", "stage": "model_answer", "retryable": True, "attempt": 1, "max_attempts": 2, "message": str(error), "details": {}, "next_action": "retry_llm", "side_effect": "none", "operator_message": None, "secondary_causes": []}
            partial = getattr(error, "_partial_text", "")
            if partial:
                recorder.emit("final_completed", "final", "partial", result_ref=recorder.result_refs({"partial": True}))
                recorder.emit("run_completed", "run", "partial", error_ref=detail.get("code"))
                return {"status": "partial", "plan": planned, "execution": execution, "answer": partial, "error": detail, "trace": recorder.events}
            recorder.emit("final_failed", "final", "failed", error_ref=detail.get("code"))
            recorder.emit("run_completed", "run", "failed", error_ref=detail.get("code"))
            return {"status": "error", "plan": planned, "execution": execution, "error": detail, "trace": recorder.events}
        outcome = "ok" if all(step.get("status") == "ok" for step in execution.get("steps", [])) else "partial"
        recorder.emit("final_completed", "final", outcome, result_ref=recorder.result_refs(execution))
        recorder.emit("run_completed", "run", outcome)
        return {"status": "ok" if outcome == "ok" else "partial", "plan": planned, "execution": execution, "answer": answer, "trace": recorder.events}
