import json
import os
import subprocess
from pathlib import Path


def _normalize_name(value):
    return " ".join(str(value).strip().split()).casefold() if isinstance(value, str) else ""


def _skill_alias(value):
    """Normalize a user skill alias without changing the PoB calculation path."""
    if not isinstance(value, str) or not value.strip():
        return value
    alias_file = Path(__file__).parents[1] / "knowledge" / "aliases" / "ko" / "skills-3.29.json"
    try:
        entries = json.loads(alias_file.read_text(encoding="utf-8")).get("entries", [])
    except (OSError, json.JSONDecodeError):
        return value.strip()
    needle = _normalize_name(value)
    matches = [entry.get("english") for entry in entries if _normalize_name(entry.get("korean")) == needle or _normalize_name(entry.get("english")) == needle]
    return matches[0] if len(matches) == 1 else value.strip()


_ERRORS = {
    "VALUE_UNAVAILABLE": ("REJECT", "tool_execution", False, "reject_request"),
    "TIMEOUT": ("RETRY_TOOL", "tool_execution", True, "retry_once"),
    "BRIDGE_PROTOCOL_ERROR": ("FATAL_INTERNAL", "bridge_protocol", False, "stop"),
    "POB_CALCULATION_ERROR": ("FATAL_INTERNAL", "pob_calculation", False, "report_error"),
    "BUILD_LOAD_FAILED": ("REJECT", "build_load", False, "reject_request"),
    "INPUT_INVALID": ("REPAIR_INPUT", "input_validation", False, "repair_input"),
    "TOOL_NOT_FOUND": ("REPAIR_INPUT", "tool_dispatch", False, "repair_input"),
    "AMBIGUOUS_ALIAS": ("ASK_USER", "context_resolution", False, "ask_user"),
    "USER_CONTEXT_MISSING": ("ASK_USER", "context_resolution", False, "ask_user"),
    "MUTATION_NOT_PERSISTENT": ("REJECT", "mutation_adapter", False, "reject_request"),
}

# One initial attempt plus at most three retries.  Only dependency failures
# that are explicitly transient may enter this loop; input, grounding, and
# mutation/state failures remain terminal.
MAX_TOOL_ATTEMPTS = 4
MUTATION_TOOLS = frozenset({"replace_item", "replace_gem", "change_passive"})
_RETRYABLE_CODES = frozenset({
    "TIMEOUT", "SEARCH_TRANSIENT", "MODEL_TRANSIENT", "TOOL_TRANSIENT",
    "RAG_TRANSIENT", "RAG_UNAVAILABLE",
})


def _primitive_fields(value):
    """Project one mapping level; never walk PoB object graphs."""
    if not isinstance(value, dict):
        return {}
    # JSON object keys are string-only at the protocol boundary. Numeric keys
    # are retained only by explicit ID projections such as allocatedNodeIds.
    return {key: item for key, item in value.items()
            if isinstance(key, str) and (item is None or isinstance(item, (str, int, float, bool)))}


def _primitive_or_none(value):
    return value if value is None or isinstance(value, (str, int, float, bool)) else None


def _sorted_ids(value, use_values=False):
    if isinstance(value, dict):
        values = value.values() if use_values else value.keys()
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = []
    result = set()
    for item in values:
        if isinstance(item, bool):
            continue
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number == item:
            result.add(number)
    return sorted(result)


def project_snapshot(context):
    """Return a deterministic primitive-only snapshot projection."""
    context = context if isinstance(context, dict) else {}
    spec = context.get("activeSpec") if isinstance(context.get("activeSpec"), dict) else {}
    projected = {
        "activeSpec": {
            "id": spec.get("id"), "title": spec.get("title"),
            "allocatedNodeIds": _sorted_ids(spec.get("allocNodes", spec.get("allocatedNodeIds"))),
            "jewelIds": _sorted_ids(spec.get("jewels", spec.get("jewelIds"))),
        },
        "activeSkillSet": _primitive_fields(context.get("activeSkillSet")),
        "activeItemSet": _primitive_fields(context.get("activeItemSet")),
        "mainSkill": _primitive_fields(context.get("mainSkill")),
        "config": _primitive_fields(context.get("config")),
        "activeBuffs": _primitive_fields(context.get("activeBuffs")),
        "enemyConditions": _primitive_fields(context.get("enemyConditions")),
        "gamePatch": _primitive_or_none(context.get("gamePatch")), "pobVersion": _primitive_or_none(context.get("pobVersion")),
        "dataRevision": _primitive_or_none(context.get("dataRevision")),
    }
    projected["activeSpec"]["id"] = _primitive_or_none(projected["activeSpec"]["id"])
    projected["activeSpec"]["title"] = _primitive_or_none(projected["activeSpec"]["title"])
    groups = context.get("socketGroups", context.get("gems", []))
    if isinstance(groups, list):
        projected["socketGroups"] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            projected_group = _primitive_fields(group)
            gems = group.get("gems")
            if isinstance(gems, list):
                gem_fields = ("order", "identity", "gemId", "variantId", "level", "quality", "qualityId", "enabled", "support", "itemGranted")
                projected_group["gems"] = [{key: gem.get(key) for key in gem_fields if key in gem and (gem[key] is None or isinstance(gem[key], (str, int, float, bool)))} for gem in gems if isinstance(gem, dict)]
            projected["socketGroups"].append(projected_group)
    return projected


def serialize_snapshot(context):
    return json.dumps(project_snapshot(context), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class PobBridgeError(RuntimeError):
    def __init__(self, message, code="UNCLASSIFIED_FAILURE", attempt=1):
        recovery, stage, retryable, next_action = _ERRORS.get(code, ("FATAL_INTERNAL", "bridge", False, "stop"))
        retryable = code in _RETRYABLE_CODES
        if retryable:
            recovery, stage, next_action = "RETRY_TOOL", "tool_execution", "retry_bounded"
        self.error = {"code": code, "recovery_class": recovery, "stage": stage, "retryable": retryable,
                      "attempt": attempt, "max_attempts": MAX_TOOL_ATTEMPTS if retryable else 1, "message": message, "details": {},
                      "next_action": next_action, "secondary_causes": [], "side_effect": "none",
                      "operator_message": None}
        super().__init__(message)


class PobUnavailableError(PobBridgeError):
    """PoB loaded the build but cannot provide the requested value."""
    def __init__(self, message):
        super().__init__(message, "VALUE_UNAVAILABLE")


class PobTimeoutError(PobBridgeError):
    """PoB calculation exceeded the bridge timeout."""
    def __init__(self, message):
        super().__init__(message, "TIMEOUT")


class PobMutationPersistenceError(PobBridgeError):
    """The one-shot XML adapter cannot make a mutation persist in live PoB."""
    def __init__(self, message="Mutation requires a persistent in-process PoB session"):
        super().__init__(message, "MUTATION_NOT_PERSISTENT")


def decode_response(stdout):
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise PobBridgeError("PoB bridge returned no JSON", "BRIDGE_PROTOCOL_ERROR")
    try:
        response = json.loads(lines[-1])
    except json.JSONDecodeError as error:
        raise PobBridgeError("PoB bridge returned invalid JSON", "BRIDGE_PROTOCOL_ERROR") from error
    if not isinstance(response, dict) or response.get("ok") is not True:
        detail = response.get("error", "PoB bridge request failed") if isinstance(response, dict) else "PoB bridge response is invalid"
        if isinstance(detail, dict):
            code, message = detail.get("code", "UNCLASSIFIED_FAILURE"), detail.get("message", "PoB bridge request failed")
        else:
            message = str(detail)
            code = "VALUE_UNAVAILABLE" if "unavailable" in message.casefold() or "no totaldps" in message.casefold() else "POB_CALCULATION_ERROR"
        if code == "VALUE_UNAVAILABLE":
            raise PobUnavailableError(message)
        raise PobBridgeError(message, code)
    return response["result"]


class PobBridge:
    def __init__(self, luajit="luajit", script_path=None, timeout=120, allow_headless_mutation=False):
        self.luajit = luajit
        self.script_path = Path(script_path or Path(__file__).parents[2] / "tools" / "agent_pob_bridge.lua")
        self.cwd = self.script_path.parents[1] / "src"
        self.timeout = timeout
        self.allow_headless_mutation = allow_headless_mutation
        self.mutation_mode = "headless" if allow_headless_mutation else "disabled"

    def call(self, build_path, tool, arguments):
        if tool in MUTATION_TOOLS and not self.allow_headless_mutation:
            raise PobMutationPersistenceError()
        arguments = dict(arguments or {})
        if "skillName" in arguments:
            arguments["skillName"] = _skill_alias(arguments["skillName"])
        payload = json.dumps({"tool": tool, "arguments": arguments}, ensure_ascii=False)
        try:
            process = subprocess.run(
                [self.luajit, str(self.script_path), str(build_path)],
                input=payload,
                text=True,
                capture_output=True,
                cwd=self.cwd,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise PobTimeoutError("PoB bridge timed out") from error
        if process.returncode != 0:
            detail = process.stderr.strip() or process.stdout.strip() or "unknown process error"
            raise PobBridgeError("PoB bridge exited with code %d: %s" % (process.returncode, detail), "BRIDGE_PROTOCOL_ERROR")
        return decode_response(process.stdout)


def make_pob_handlers(build_path, luajit=None, timeout=120, allow_headless_mutation=False):
    bridge = PobBridge(luajit or os.getenv("LUAJIT", "luajit"), timeout=timeout, allow_headless_mutation=allow_headless_mutation)
    return {name: (lambda arguments, name=name: bridge.call(build_path, name, arguments)) for name in (
        "get_character_stats", "get_skill_stats", "get_skill_dps", "get_highest_dps_skill",
        "get_skill_breakdown", "get_item_modifiers", "get_projectile_behavior", "get_trigger_sequence",
        "get_curse_application_order", "get_ailment_effect", "get_damage_breakdown", "get_conversion_chain",
        "get_effective_resistance", "get_support_links", "resolve_skill_context", "get_projectile_count",
        "get_curse_limit", "get_elemental_penetration", "get_skill_chain", "get_socket_order",
        "compare_support_effect", "explain_damage_change",
        "compare_build_states",
        "replace_item",
        "replace_gem",
        "change_passive",
        "get_duration", "explain_stat",
    )}
