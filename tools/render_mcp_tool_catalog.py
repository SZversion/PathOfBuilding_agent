"""Render the executable MCP contracts into the human tool catalog."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- MCP TOOL CONTRACTS START -->"
END = "<!-- MCP TOOL CONTRACTS END -->"


def render():
    sys.path.insert(0, str(ROOT))
    from agent.tool_catalog import TOOL_CATALOG

    lines = ["## Generated MCP contracts", "", "These executable schemas are generated from `agent/tool_catalog.py`.", ""]
    for name, spec in sorted(TOOL_CATALOG.items()):
        lines.extend([f"### `{name}`", "", f"- Category: `{spec.category}`; provider: `{spec.group}`",
                      f"- Purpose: {spec.purpose}", f"- When: {spec.when_to_use}",
                      f"- Constraints: {spec.constraints}", f"- Returns: {spec.returns}",
                      f"- Side effect: `{spec.side_effect}`; idempotent: `{str(spec.idempotent).lower()}`; timeout: {spec.timeout_seconds}s",
                      f"- Retry: `{spec.retry_policy}`; errors: {', '.join(f'`{code}`' for code in spec.error_codes)}",
                      f"- Example: `{spec.examples[0]}`",
                      "- Input schema:", "", "```json", __import__("json").dumps(spec.input_schema, ensure_ascii=False, indent=2), "```", ""])
    return START + "\n" + "\n".join(lines) + END


def update(check=False):
    path = ROOT / "docs" / "tools" / "catalog.md"
    text = path.read_text(encoding="utf-8")
    section = render()
    if START in text and END in text:
        prefix, rest = text.split(START, 1)
        _, suffix = rest.split(END, 1)
        updated = prefix + section + suffix
    else:
        updated = text.rstrip() + "\n\n" + section + "\n"
    if check:
        if text != updated:
            print("generated MCP catalog is stale", file=sys.stderr)
            return 1
    else:
        path.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(update("--check" in sys.argv))
