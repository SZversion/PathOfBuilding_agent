import json
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


def read_skill(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing skill metadata: {path}")
    metadata, separator, body = text[4:].partition("\n---\n")
    fields = {}
    for line in metadata.splitlines():
        key, colon, value = line.partition(":")
        if colon and key in {"name", "description"}:
            fields[key] = value.strip()
    if not separator or not fields.get("name") or not fields.get("description") or not body.strip():
        raise ValueError(f"skill requires name, description, and body: {path}")
    return fields, body.strip()


def discover_skills():
    registry = {}
    for path in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
        if path.parent.name == "common":
            continue
        metadata, _ = read_skill(path)
        name = metadata["name"]
        if name in registry:
            raise ValueError(f"duplicate skill name: {name}")
        registry[name] = {**metadata, "path": path}
    return registry


def selection_instructions():
    _, body = read_skill(SKILLS_ROOT / "common" / "SKILL.md")
    return body.split("\n## Selection\n", 1)[1].split("\n## Planner\n", 1)[0].strip()


def selection_schema(registry):
    path = SKILLS_ROOT.parent / "schemas" / "skill-selection.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    schema["properties"]["skills"]["items"]["enum"] = sorted(registry)
    return schema


def selected_instructions(value, registry):
    if not isinstance(value, dict) or set(value) != {"skills"}:
        raise ValueError("skill selection must contain only skills")
    names = value["skills"]
    if not isinstance(names, list) or any(not isinstance(name, str) or name not in registry for name in names):
        raise ValueError("skill selection contains an unavailable skill")
    if len(names) != len(set(names)):
        raise ValueError("skill selection contains duplicate skills")
    return "\n\n".join(read_skill(registry[name]["path"])[1] for name in names)
