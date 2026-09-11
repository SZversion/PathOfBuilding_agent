import json

from .runtime import SnapshotSync, execute_plan


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
MUTATION_TOOLS = frozenset({"replace_item", "replace_gem", "change_passive"})
READ_ONLY_TOOLS = frozenset(ALLOWED_TOOLS - MUTATION_TOOLS)
PLAN_FIELDS = frozenset({"intent", "steps", "metadata"})
STEP_FIELDS = frozenset({"tool", "arguments", "expectedSnapshotRevision"})
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

TOOL_MIN_ARGUMENTS = {tool: {} for tool in READ_ONLY_TOOLS}
for _tool in REQUIRED_ARGUMENTS:
    TOOL_MIN_ARGUMENTS[_tool] = {"required": list(REQUIRED_ARGUMENTS[_tool]), "types": {key: "string" for key in REQUIRED_ARGUMENTS[_tool]}}
TOOL_MIN_ARGUMENTS["compare_build_states"] = {"required": ["beforeState", "afterState"], "types": {"beforeState": "object|string", "afterState": "object|string"}}

_PLANNER_CATALOG = json.dumps(
    {tool: TOOL_MIN_ARGUMENTS[tool] for tool in sorted(READ_ONLY_TOOLS)},
    ensure_ascii=False, sort_keys=True, separators=(",", ":"),
)
PLANNER_SYSTEM = f"""You are a PoE Path of Building read-only tool planner. Return JSON only: {{\"intent\": string, \"steps\": [{{\"tool\": string, \"arguments\": object, \"expectedSnapshotRevision\": string|null}}]}}. Use ONLY the canonical Tool names in this registry and its minimum argument schema: {_PLANNER_CATALOG}. Never invent, translate, or paraphrase Tool names. Never return mutation Tools, free-text commands, raw XML, or PoB numbers. Valid example: {{\"intent\":\"pob_stat\",\"steps\":[{{\"tool\":\"get_curse_limit\",\"arguments\":{{}}}}]}}."""
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


def validate_plan(value):
    if not isinstance(value, dict) or not isinstance(value.get("steps"), list):
        raise PlanValidationError("plan.steps must be a list")
    if "intent" in value and not isinstance(value["intent"], str):
        raise PlanValidationError("plan.intent must be a string")
    if "metadata" in value and not isinstance(value["metadata"], dict):
        raise PlanValidationError("plan.metadata must be an object")
    unknown_plan_fields = set(value) - PLAN_FIELDS
    if unknown_plan_fields:
        raise PlanValidationError("unsupported plan fields", details={"fields": sorted(unknown_plan_fields)})
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
        _validate_arguments(tool, step.get("arguments"))
        revision = step.get("expectedSnapshotRevision")
        if revision is not None and (not isinstance(revision, str) or not revision.strip()):
            raise PlanValidationError("expectedSnapshotRevision must be a non-empty string or null")
        signature = (tool, _canonical_arguments(step["arguments"]))
        revisions = seen.setdefault(signature, set())
        if revision in revisions:
            raise PlanValidationError("exact duplicate tool call", code="DUPLICATE_TOOL_CALL")
        revisions.add(revision)
    return value


class AgentLoop:
    def __init__(self, model, *, snapshot_provider=None):
        if not hasattr(model, "chat"):
            raise TypeError("model must provide chat(messages)")
        self.model = model
        self.snapshot_provider = snapshot_provider
        self.snapshot_sync = SnapshotSync()

    def _chat(self, messages, *, attempts=2):
        last = None
        for attempt in range(1, attempts + 1):
            try:
                return self.model.chat(messages)
            except Exception as error:
                last = error
                detail = getattr(error, "error", {})
                if detail.get("retryable") is not True or attempt >= attempts:
                    raise
        raise last

    def run(self, question, search=None, handlers=None, *, snapshot=None, current_revision=None):
        if not isinstance(question, str) or not question.strip():
            return {"status": "plan_error", "error": "question is required"}
        if snapshot is None and callable(self.snapshot_provider):
            snapshot = self.snapshot_provider()
        sync = self.snapshot_sync.prepare(snapshot) if snapshot is not None else None
        planning_payload = {"question": question}
        if sync is not None:
            planning_payload["context"] = sync
        last_error = None
        for llm_attempt in range(1, 3):
            try:
                planned = validate_plan(_json_object(self._chat([
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": json.dumps(planning_payload, ensure_ascii=False)},
                ])))
                break
            except PlanValidationError as error:
                return {"status": "error", "error": {"code": error.code, "recovery_class": "REJECT" if error.code == "MUTATION_NOT_PERSISTENT" else "REPAIR_INPUT", "stage": "plan_validation", "retryable": False, "attempt": 1, "max_attempts": 1, "message": str(error), "details": error.details, "next_action": "reject_request" if error.code == "MUTATION_NOT_PERSISTENT" else "repair_input", "side_effect": "none", "operator_message": None, "secondary_causes": []}}
            except Exception as error:
                last_error = error
                if llm_attempt == 2:
                    detail = getattr(error, "error", None) or {"code": "RETRY_LLM", "recovery_class": "RETRY_LLM", "stage": "model_plan", "retryable": False, "attempt": llm_attempt, "max_attempts": 2, "message": str(error), "details": {}, "next_action": "human_review", "side_effect": "none", "operator_message": None, "secondary_causes": []}
                    detail = dict(detail)
                    detail["attempt"] = llm_attempt
                    return {"status": "plan_error", "error": detail}
        if last_error is not None and "planned" not in locals():
            return {"status": "plan_error", "error": {"code": "RETRY_LLM", "recovery_class": "RETRY_LLM", "stage": "model_plan", "retryable": False, "attempt": 2, "max_attempts": 2, "message": str(last_error), "details": {}, "next_action": "human_review", "side_effect": "none", "operator_message": None, "secondary_causes": []}}
        execution = execute_plan(question, planned, search=search, handlers=handlers,
                                 snapshot_revision_value=(sync or {}).get("snapshotRevision"),
                                 current_revision=current_revision)
        answer_payload = {"question": question, "results": _model_safe_execution(execution)}
        try:
            answer = self._chat([
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps(answer_payload, ensure_ascii=False)},
            ])
        except Exception as error:
            detail = getattr(error, "error", None) or {"code": "RETRY_LLM", "recovery_class": "RETRY_LLM", "stage": "model_answer", "retryable": True, "attempt": 1, "max_attempts": 2, "message": str(error), "details": {}, "next_action": "retry_llm", "side_effect": "none", "operator_message": None, "secondary_causes": []}
            return {"status": "error", "plan": planned, "execution": execution, "error": detail}
        return {"status": "ok", "plan": planned, "execution": execution, "answer": answer}
