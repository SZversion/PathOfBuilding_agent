"""Static consistency check for the public PoE Agent Tool catalog."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "tools" / "catalog.md"
LOOP = ROOT / "agent" / "orchestration" / "agent_loop.py"
CATALOG_SOURCE = ROOT / "agent" / "tool_catalog.py"
LUA_BRIDGE = ROOT / "src" / "Modules" / "AgentBridge.lua"


def public_names(text):
    section = text.split("## Planned Tools", 1)[0]
    return set(re.findall(r"\|\s*`([a-z][a-z0-9_]*)`\s*\|", section))


def lint():
    sys.path.insert(0, str(ROOT))
    from agent.tool_catalog import ALLOWED_TOOLS, TOOL_CATALOG, TOOL_GROUPS
    from tools.render_mcp_tool_catalog import update as check_generated_catalog

    catalog = CATALOG.read_text(encoding="utf-8")
    public = public_names(catalog)
    allowed = set(ALLOWED_TOOLS)
    groups = {spec.group for spec in TOOL_CATALOG.values()}
    lua = LUA_BRIDGE.read_text(encoding="utf-8").split("local revisions", 1)[0]
    lua_names = set(re.findall(r"([a-z][a-z0-9_]*)\s*=\s*true", lua))
    pob_names = {name for name, spec in TOOL_CATALOG.items() if spec.group == "pob_live"}
    required = {"What", "When", "How", "Output", "Constraints", "sideEffect", "riskLevel"}
    errors = []
    exception_contract = (ROOT / "agent" / "EXCEPTION_HANDLING.md").read_text(encoding="utf-8")
    stable_section = exception_contract.split("### 2.1 Stable recovery and leaf-code registry", 1)[-1].split("## 3.", 1)[0]
    registered_errors = set(re.findall(r"`([A-Z][A-Z0-9_]+)`", stable_section))
    if check_generated_catalog(check=True):
        errors.append("generated MCP tool contracts are stale; run tools/render_mcp_tool_catalog.py")
    valid_categories = {"context_resolution", "state_metadata", "calculation", "trace_evidence",
                        "comparison_simulation", "mutation", "knowledge_search"}
    for name, spec in TOOL_CATALOG.items():
        if spec.category not in valid_categories:
            errors.append(f"{name}: unknown semantic category {spec.category}")
        if not (spec.purpose and spec.when_to_use and spec.constraints and spec.returns):
            errors.append(f"{name}: incomplete model-facing description contract")
        if spec.timeout_seconds <= 0 or spec.retry_policy not in {"never", "transient_read_only"}:
            errors.append(f"{name}: invalid timeout or retry policy")
        if spec.retry_policy != "never" and (spec.side_effect != "read_only" or not spec.idempotent):
            errors.append(f"{name}: retry policy is unsafe for its side effect/idempotency")
        if not spec.error_codes or not spec.examples:
            errors.append(f"{name}: missing error vocabulary or example")
        unregistered = set(spec.error_codes) - registered_errors
        if unregistered:
            errors.append(f"{name}: unregistered error codes {', '.join(sorted(unregistered))}")
        for field, schema in spec.input_schema.get("properties", {}).items():
            if not schema.get("description", "").strip():
                errors.append(f"{name}.{field}: missing field description")
    contract_lines = {name: line for line in catalog.splitlines() if line.startswith("- `")
                      for name in re.findall(r"`([a-z][a-z0-9_]*)`", line)}
    for name in sorted(public):
        line = contract_lines.get(name, "")
        missing = required - set(re.findall(r"[A-Za-z]+", line))
        if missing:
            errors.append(f"{name}: missing contract fields {', '.join(sorted(missing))}")
    for name in sorted(public - allowed):
        errors.append(f"{name}: missing from planner allowlist")
    if set(TOOL_CATALOG) != allowed:
        errors.append("canonical tool catalog and AgentLoop allowlist differ")
    if not groups <= TOOL_GROUPS:
        errors.append("canonical catalog references an unregistered handler group")
    if pob_names != lua_names:
        errors.append(f"PoB MCP group and Lua read-only dispatch differ (catalog-only={sorted(pob_names-lua_names)}, Lua-only={sorted(lua_names-pob_names)})")
    if public != allowed:
        errors.append(f"documentation and canonical catalog differ (docs-only={sorted(public-allowed)}, catalog-only={sorted(allowed-public)})")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"catalog lint passed ({len(public)} public tools; {len(pob_names)} Lua PoB tools)")
    return 0


if __name__ == "__main__":
    raise SystemExit(lint())
