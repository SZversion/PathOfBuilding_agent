"""MCP registry and argument validation backed by the shared tool catalog."""

from __future__ import annotations

from agent.orchestration.agent_loop import SKILL_AWARE_READ_ONLY_TOOLS
from agent.tool_catalog import ALLOWED_TOOLS, TOOL_CATALOG


class ToolContractError(ValueError):
    """A tool name or argument object does not match its advertised contract."""


def tool_definitions() -> list[dict]:
    """Return MCP-ready definitions directly from the canonical catalog."""
    return [TOOL_CATALOG[name].as_mcp_definition() for name in sorted(TOOL_CATALOG)]


def _matches(value, schema: dict) -> bool:
    if "anyOf" in schema:
        return any(_matches(value, candidate) for candidate in schema["anyOf"])
    expected = schema.get("type")
    if expected == "string": return isinstance(value, str)
    if expected == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean": return isinstance(value, bool)
    if expected == "object": return isinstance(value, dict)
    if expected == "array": return isinstance(value, list)
    return False


def validate_tool_call(name: str, arguments: dict) -> dict:
    """Validate arguments using the same schema exposed through MCP."""
    if name not in ALLOWED_TOOLS:
        raise ToolContractError("unknown tool: " + str(name))
    if not isinstance(arguments, dict):
        raise ToolContractError("tool arguments must be an object")
    if any(not isinstance(key, str) for key in arguments):
        raise ToolContractError("tool argument keys must be strings")
    if {"command", "freeText", "prompt", "rawXml"} & set(arguments):
        raise ToolContractError("free-text or raw PoB input is not allowed")
    args = dict(arguments)
    if "skill" in args:
        if name not in SKILL_AWARE_READ_ONLY_TOOLS:
            raise ToolContractError("skill shorthand is not supported for this tool")
        skill = args.pop("skill")
        if not isinstance(skill, str):
            raise ToolContractError("skill must be a string")
        if "skillName" in args and args["skillName"].casefold() != skill.casefold():
            raise ToolContractError("skill and skillName conflict")
        args.setdefault("skillName", skill)
    schema = TOOL_CATALOG[name].input_schema
    properties = schema["properties"]
    unknown = set(args) - set(properties)
    if unknown:
        raise ToolContractError("unsupported tool arguments: " + ", ".join(sorted(unknown)))
    for key, value in args.items():
        field = properties[key]
        if not _matches(value, field):
            raise ToolContractError("argument has invalid type: " + key)
        if "enum" in field and value not in field["enum"]:
            raise ToolContractError("argument has unsupported value: " + key)
        if isinstance(value, int) and not isinstance(value, bool):
            if value < field.get("minimum", value) or value > field.get("maximum", value):
                raise ToolContractError("argument is outside allowed range: " + key)
        if isinstance(value, str):
            if len(value) < field.get("minLength", 0) or len(value) > field.get("maxLength", len(value)):
                raise ToolContractError("argument has invalid length: " + key)
        if isinstance(value, list) and "items" in field:
            if any(not _matches(item, field["items"]) for item in value):
                raise ToolContractError("argument has invalid item type: " + key)
    for key in schema.get("required", ()):
        if key not in args or (isinstance(args[key], str) and not args[key].strip()):
            raise ToolContractError("required argument is missing or invalid: " + key)
    alternatives = schema.get("anyOf", ())
    if alternatives and not any(all(key in args for key in candidate.get("required", ()))
                                for candidate in alternatives):
        raise ToolContractError("one of the alternative required arguments is missing")
    return args
