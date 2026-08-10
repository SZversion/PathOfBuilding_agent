import json

from .runtime import execute_plan


ALLOWED_TOOLS = frozenset({
    "search_knowledge", "get_projectile_count", "get_curse_limit", "get_elemental_penetration",
    "get_socket_order", "get_skill_chain", "compare_support_effect", "explain_damage_change",
    "get_skill_dps", "get_highest_dps_skill", "get_skill_breakdown", "get_item_modifiers",
    "get_projectile_behavior", "get_trigger_sequence", "get_curse_application_order", "get_ailment_effect",
    "get_damage_breakdown", "get_conversion_chain", "get_effective_resistance", "get_support_links",
})
TOOL_ALIASES = {tool.replace("_", ""): tool for tool in ALLOWED_TOOLS}
TOOL_ALIASES.update({"getCurseLimit": "get_curse_limit", "getProjectileCount": "get_projectile_count", "getElementalPenetration": "get_elemental_penetration", "searchKnowledge": "search_knowledge", "getSocketOrder": "get_socket_order", "getSkillChain": "get_skill_chain", "compareSupportEffect": "compare_support_effect", "explainDamageChange": "explain_damage_change"})
MAX_STEPS = 8
PLANNER_SYSTEM = """You are a PoE Path of Building tool planner. Return JSON only: {\"intent\": string, \"steps\": [{\"tool\": string, \"arguments\": object}]}. Use only the registered tools. Do not answer the user or invent PoB numbers."""
ANSWER_SYSTEM = """Answer the user's PoE question using only the supplied Tool results and knowledge documents. By default, answer in Korean using friendly and clear wording. Distinguish calculated values, applied effects, and calculation evidence. If a result is unavailable or an input is ambiguous, state that plainly and do not guess. Answer Korean questions in Korean."""


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


def validate_plan(value):
    if not isinstance(value, dict) or not isinstance(value.get("steps"), list):
        raise ValueError("plan.steps must be a list")
    steps = value["steps"]
    if len(steps) > MAX_STEPS:
        raise ValueError("plan has too many steps")
    seen = set()
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("tool"), str):
            raise ValueError("each step needs a tool")
        tool = TOOL_ALIASES.get(step["tool"], step["tool"])
        step["tool"] = tool
        if tool not in ALLOWED_TOOLS:
            raise ValueError("tool is not allowed: " + tool)
        if tool in seen:
            raise ValueError("duplicate tool: " + tool)
        seen.add(tool)
        if not isinstance(step.get("arguments"), dict):
            raise ValueError("tool arguments must be an object")
    return value


class AgentLoop:
    def __init__(self, model):
        if not hasattr(model, "chat"):
            raise TypeError("model must provide chat(messages)")
        self.model = model

    def run(self, question, search=None, handlers=None):
        if not isinstance(question, str) or not question.strip():
            return {"status": "plan_error", "error": "question is required"}
        try:
            planned = validate_plan(_json_object(self.model.chat([
                {"role": "system", "content": PLANNER_SYSTEM},
                {"role": "user", "content": question},
            ])))
        except (ValueError, RuntimeError) as error:
            return {"status": "plan_error", "error": str(error)}
        execution = execute_plan(question, planned, search=search, handlers=handlers)
        answer = self.model.chat([
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps({"question": question, "plan": planned, "results": execution}, ensure_ascii=False)},
        ])
        return {"status": "ok", "plan": planned, "execution": execution, "answer": answer}
