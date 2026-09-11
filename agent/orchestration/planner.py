import re


# Contract shared by the external planner and local dispatcher.  The runtime
# remains the authority; this declaration is intentionally read-only.
PLAN_SCHEMA = {
    "type": "object",
    "required": ["steps"],
    "properties": {
        "intent": {"type": "string"},
        "steps": {"type": "array", "maxItems": 8},
        "metadata": {"type": "object"},
    },
    "additionalProperties": False,
    "items": {
        "type": "object",
        "required": ["tool", "arguments"],
        "properties": {
            "tool": {"type": "string"},
            "arguments": {"type": "object"},
            "expectedSnapshotRevision": {"type": ["string", "null"]},
        },
        "additionalProperties": False,
    },
}


SKILLS = ("Poisonous Concoction of Bouncing", "Impending Doom")
SUPPORTS = ("Greater Volley", "Greater Multiple Projectiles")


def validate_plan(value):
    """Public schema entry point; implementation stays with the dispatcher."""
    from .agent_loop import validate_plan as _validate_plan
    return _validate_plan(value)


def _find(text, values):
    lowered = text.casefold()
    return next((value for value in values if value.casefold() in lowered), None)


def plan(question):
    if not isinstance(question, str) or not question.strip():
        return {"intent": "unknown", "entities": {}, "steps": [], "confidence": 0.0}
    lowered = question.casefold()
    skill = _find(question, SKILLS)
    support = _find(question, SUPPORTS)
    entities = {key: value for key, value in (("skillName", skill), ("supportName", support)) if value}
    set_match = re.search(r"\b(\d+\)\s*(?:endgame setup|pconc of bouncing swap))", question, re.I)
    if set_match:
        entities["skillSetSelector"] = set_match.group(1)
    if support and any(word in lowered for word in ("딜", "피해", "감소", "줄", "연쇄", "damage")):
        return {"intent": "mechanism_compare", "entities": entities, "steps": [
            {"tool": "compare_support_effect", "arguments": entities},
            {"tool": "explain_damage_change", "arguments": entities},
        ], "confidence": 0.95}
    if any(word in lowered for word in ("아이템", "한국어", "이름", "고유", "플라스크")) and not any(word in lowered for word in ("몇", "계산", "왜")):
        return {"intent": "item_alias", "entities": {"query": question}, "steps": [
            {"tool": "resolve_item_alias", "arguments": {"query": question}},
        ], "confidence": 0.9}
    if any(word in lowered for word in ("투사체", "projectile")):
        entities["stat"] = "ProjectileCount"
        return {"intent": "pob_stat", "entities": entities, "steps": [{"tool": "get_projectile_count", "arguments": entities}], "confidence": 0.9}
    if any(word in lowered for word in ("저주", "curse")) and any(word in lowered for word in ("한도", "개수", "몇")):
        entities["stat"] = "EnemyCurseLimit"
        return {"intent": "pob_stat", "entities": entities, "steps": [{"tool": "get_curse_limit", "arguments": entities}], "confidence": 0.9}
    if any(word in lowered for word in ("왜", "규칙", "저항", "피해", "타격", "지속")):
        return {"intent": "rule_search", "entities": {"query": question}, "steps": [{"tool": "search_knowledge", "arguments": {"query": question}}], "confidence": 0.65}
    return {"intent": "unknown", "entities": entities, "steps": [], "confidence": 0.0}
