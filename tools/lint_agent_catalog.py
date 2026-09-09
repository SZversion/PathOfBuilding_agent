"""Static consistency check for the public PoE Agent Tool catalog."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "tools" / "catalog.md"
LOOP = ROOT / "agent" / "orchestration" / "agent_loop.py"
BRIDGE = ROOT / "agent" / "pob" / "bridge.py"


def public_names(text):
    section = text.split("## Planned Tools", 1)[0]
    return set(re.findall(r"\|\s*`([a-z][a-z0-9_]*)`\s*\|", section))


def allowlist_names(text):
    block = text.split("ALLOWED_TOOLS", 1)[1].split("})", 1)[0]
    return set(re.findall(r'"([a-z][a-z0-9_]*)"', block))


def handler_names(text):
    if "for name in (" not in text:
        return set()
    block = text.split("for name in (", 1)[1].split(")", 1)[0]
    return set(re.findall(r'"([a-z][a-z0-9_]*)"', block))


def lint():
    catalog = CATALOG.read_text(encoding="utf-8")
    public = public_names(catalog)
    allowed = allowlist_names(LOOP.read_text(encoding="utf-8"))
    handlers = handler_names(BRIDGE.read_text(encoding="utf-8"))
    required = {"What", "When", "How", "Output", "Constraints", "sideEffect", "riskLevel"}
    errors = []
    contract_lines = {name: line for line in catalog.splitlines() if line.startswith("- `")
                      for name in re.findall(r"`([a-z][a-z0-9_]*)`", line)}
    for name in sorted(public):
        line = contract_lines.get(name, "")
        missing = required - set(re.findall(r"[A-Za-z]+", line))
        if missing:
            errors.append(f"{name}: missing contract fields {', '.join(sorted(missing))}")
    for name in sorted(public - allowed):
        errors.append(f"{name}: missing from planner allowlist")
    for name in sorted(public - handlers):
        errors.append(f"{name}: missing from Bridge handlers")
    for name in sorted((allowed & handlers) - public):
        errors.append(f"{name}: registered public handler is absent from catalog")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"catalog lint passed ({len(public)} public tools)")
    return 0


if __name__ == "__main__":
    raise SystemExit(lint())
