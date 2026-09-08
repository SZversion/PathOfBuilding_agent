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
}


class PobBridgeError(RuntimeError):
    def __init__(self, message, code="UNCLASSIFIED_FAILURE", attempt=1):
        recovery, stage, retryable, next_action = _ERRORS.get(code, ("FATAL_INTERNAL", "bridge", False, "stop"))
        self.error = {"code": code, "recovery_class": recovery, "stage": stage, "retryable": retryable,
                      "attempt": attempt, "max_attempts": 1, "message": message, "details": {},
                      "next_action": next_action, "secondary_causes": []}
        super().__init__(message)


class PobUnavailableError(PobBridgeError):
    """PoB loaded the build but cannot provide the requested value."""
    def __init__(self, message):
        super().__init__(message, "VALUE_UNAVAILABLE")


class PobTimeoutError(PobBridgeError):
    """PoB calculation exceeded the bridge timeout."""
    def __init__(self, message):
        super().__init__(message, "TIMEOUT")


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
    def __init__(self, luajit="luajit", script_path=None, timeout=120):
        self.luajit = luajit
        self.script_path = Path(script_path or Path(__file__).parents[2] / "tools" / "agent_pob_bridge.lua")
        self.cwd = self.script_path.parents[1] / "src"
        self.timeout = timeout

    def call(self, build_path, tool, arguments):
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


def make_pob_handlers(build_path, luajit=None, timeout=120):
    bridge = PobBridge(luajit or os.getenv("LUAJIT", "luajit"), timeout=timeout)
    return {name: (lambda arguments, name=name: bridge.call(build_path, name, arguments)) for name in (
        "get_character_stats", "get_skill_stats", "get_skill_dps", "get_highest_dps_skill",
        "get_skill_breakdown", "get_item_modifiers", "get_projectile_behavior", "get_trigger_sequence",
        "get_curse_application_order", "get_ailment_effect", "get_damage_breakdown", "get_conversion_chain",
        "get_effective_resistance", "get_support_links", "resolve_skill_context", "get_projectile_count",
        "get_curse_limit", "get_elemental_penetration", "get_skill_chain", "get_socket_order",
        "compare_support_effect", "explain_damage_change",
        "get_duration", "explain_stat",
    )}
