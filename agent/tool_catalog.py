"""Single source of truth for public PoE tool contracts and handler groups."""
from __future__ import annotations
from dataclasses import dataclass

_TOOL_RECORDS = [{'name': 'search_knowledge',
  'description': 'Search the local versioned Path of Exile rules and mechanics knowledge base.',
  'group': 'knowledge',
  'arguments': {'query': 'string', 'limit': 'integer', 'category': 'string'},
  'required': ('query',)},
 {'name': 'search_external',
  'description': 'Search PoE Wiki and PoEDB and return matching page bodies with source URLs.',
  'group': 'external_search',
  'arguments': {'query': 'string', 'source': 'string', 'limit': 'integer'},
  'required': ('query',)},
 {'name': 'resolve_item_alias',
  'description': 'Resolve an exact Korean or English item alias to its canonical identity.',
  'group': 'knowledge',
  'arguments': {'query': 'string', 'category': 'string'},
  'required': ('query',)},
 {'name': 'resolve_skill_alias',
  'description': 'Resolve an exact Korean or English skill alias to its canonical gem identity.',
  'group': 'knowledge',
  'arguments': {'query': 'string'},
  'required': ('query',)},
 {'name': 'get_character_stats',
  'description': 'Read character statistics calculated by the active Path of Building session.',
  'group': 'pob_live',
  'arguments': {},
  'required': ()},
 {'name': 'get_skill_stats',
  'description': 'Read calculated output and gem metadata for a selected skill.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_skill_dps',
  'description': "Read PoB's calculated DPS for a selected skill.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_highest_dps_skill',
  'description': 'Find the active skill with the highest calculated PoB DPS.',
  'group': 'pob_live',
  'arguments': {},
  'required': ()},
 {'name': 'get_skill_breakdown',
  'description': "Read PoB's calculation breakdown for a selected skill.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_item_modifiers',
  'description': 'Read modifier lines from an item in the active build.',
  'group': 'pob_live',
  'arguments': {'itemId': 'integer'},
  'required': ('itemId',)},
 {'name': 'get_projectile_behavior',
  'description': 'Read projectile count, pierce, chain, fork, and split outputs.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_trigger_sequence',
  'description': 'Read trigger metadata and sequence fields for a skill.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_curse_application_order',
  'description': 'Read socket order relevant to curse application; does not simulate timing.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string'},
  'required': ('skillName',)},
 {'name': 'get_ailment_effect',
  'description': 'Read calculated ailment values and chances for a skill.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_damage_breakdown',
  'description': "Read PoB's damage breakdown for a selected skill.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_conversion_chain',
  'description': "Read PoB's damage conversion and gain chain for a skill.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_effective_resistance',
  'description': "Read PoB's effective resistance multipliers.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_support_links',
  'description': 'Read the active support links for a selected skill.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string'},
  'required': ('skillName',)},
 {'name': 'resolve_skill_context',
  'description': 'Resolve a skill name to its active PoB skill context.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string'},
  'required': ('skillName',)},
 {'name': 'get_projectile_count',
  'description': "Read PoB's calculated projectile count for a skill.",
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_curse_limit',
  'description': "Read the active build's calculated curse limit.",
  'group': 'pob_live',
  'arguments': {},
  'required': ()},
 {'name': 'get_elemental_penetration',
  'description': 'Read calculated elemental penetration for a skill.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer', 'skillName': 'string', 'skillSetSelector': 'string'},
  'required': ()},
 {'name': 'get_skill_chain',
  'description': 'Read chain values for a skill in a selected Skill Set.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string'},
  'required': ('skillName',)},
 {'name': 'get_socket_order',
  'description': "Read PoB's socket and synthetic group order for a skill.",
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string'},
  'required': ('skillName',)},
 {'name': 'compare_support_effect',
  'description': 'Compare PoB-calculated outputs with and without a support gem.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string', 'supportName': 'string'},
  'required': ('skillName', 'supportName')},
 {'name': 'explain_damage_change',
  'description': 'Return PoB calculation evidence for a support-related damage change.',
  'group': 'pob_live',
  'arguments': {'skillSetSelector': 'string', 'skillName': 'string', 'supportName': 'string'},
  'required': ('skillName', 'supportName')},
 {'name': 'compare_build_states',
  'description': 'Compare two supplied PoB snapshots and report output deltas.',
  'group': 'snapshot_compare',
  'arguments': {'beforeState': 'object|string',
                'afterState': 'object|string',
                'skillIndex': 'integer',
                'comparisonFields': 'array'},
  'required': ('beforeState', 'afterState', 'skillIndex')},
 {'name': 'replace_item',
  'description': 'Request an item replacement; live execution is currently capability-gated.',
  'group': 'mutation',
  'arguments': {'slot': 'string',
                'itemIdentity': 'string',
                'itemText': 'string',
                'expectedSnapshotRevision': 'string',
                'idempotencyKey': 'string',
                'fingerprint': 'string'},
  'required': ('slot',
               'itemIdentity',
               'itemText',
               'expectedSnapshotRevision',
               'idempotencyKey',
               'fingerprint')},
 {'name': 'replace_gem',
  'description': 'Request a gem replacement; live execution is currently capability-gated.',
  'group': 'mutation',
  'arguments': {'socketGroup': 'integer|string',
                'gemIdentity': 'string',
                'level': 'integer',
                'quality': 'integer',
                'enabled': 'boolean',
                'expectedSnapshotRevision': 'string',
                'idempotencyKey': 'string',
                'fingerprint': 'string'},
  'required': ('socketGroup',
               'gemIdentity',
               'level',
               'quality',
               'expectedSnapshotRevision',
               'idempotencyKey',
               'fingerprint')},
 {'name': 'change_passive',
  'description': 'Request a passive or jewel change; live execution is currently capability-gated.',
  'group': 'mutation',
  'arguments': {'operation': 'string',
                'nodeId': 'integer',
                'socketNodeId': 'integer',
                'itemId': 'integer',
                'expectedSnapshotRevision': 'string',
                'idempotencyKey': 'string',
                'fingerprint': 'string'},
  'required': ('operation', 'expectedSnapshotRevision', 'idempotencyKey', 'fingerprint')},
 {'name': 'get_duration',
  'description': 'Read a selected skill duration and its PoB breakdown.',
  'group': 'pob_live',
  'arguments': {'skillIndex': 'integer',
                'skillName': 'string',
                'skillSetSelector': 'string',
                'durationType': 'string'},
  'required': ('durationType',)},
 {'name': 'explain_stat',
  'description': 'Read a stat value and the PoB modifier trace supporting it.',
  'group': 'pob_live',
  'arguments': {'stat': 'string',
                'skillIndex': 'integer',
                'skillName': 'string',
                'skillSetSelector': 'string'},
  'required': ('stat',)}]
TOOL_GROUPS = frozenset({"pob_live", "knowledge", "external_search", "snapshot_compare", "mutation"})

def _json_type(type_name: str) -> dict:
    if type_name == "object|string": return {"anyOf": [{"type": "object"}, {"type": "string"}]}
    if type_name == "integer|string": return {"anyOf": [{"type": "integer"}, {"type": "string"}]}
    return {"type": {"string":"string", "integer":"integer", "boolean":"boolean", "object":"object", "array":"array"}[type_name]}

def _field_description(name: str, field: str) -> str:
    descriptions = {
        "query": "Item, skill, mechanic, or page text to look up.",
        "limit": "Maximum number of results to return.",
        "category": "Optional knowledge category used to narrow the lookup.",
        "source": "External source selection: PoEDB, PoE Wiki, or both.",
        "skillIndex": "One-based skill index in the selected Skill Set.",
        "skillName": "Skill name used to resolve the active skill context.",
        "skillSetSelector": "Optional Skill Set selector; defaults to the active set.",
        "itemId": "PoB item identifier from the current build snapshot.",
        "durationType": "Duration field to explain, such as skill or debuff duration.",
        "stat": "PoB stat identifier or supported stat name to trace.",
        "socketGroup": "Socket group index or supported group selector.",
        "supportName": "Support gem name to evaluate against the selected skill.",
        "beforeState": "First normalized PoB snapshot or its serialized representation.",
        "afterState": "Second normalized PoB snapshot or its serialized representation.",
        "comparisonFields": "Optional output fields to include in the comparison.",
        "slot": "Equipment slot to target in the proposed replacement.",
        "itemIdentity": "Canonical identity of the proposed item.",
        "itemText": "Serialized item text for the proposed replacement.",
        "expectedSnapshotRevision": "Snapshot revision the proposal was based on.",
        "idempotencyKey": "Caller-generated key identifying this mutation request.",
        "fingerprint": "Build or target fingerprint used to validate the proposal.",
        "gemIdentity": "Canonical identity of the proposed gem.",
        "level": "Gem level for the proposed change.",
        "quality": "Gem quality for the proposed change.",
        "enabled": "Whether the gem should be enabled in the proposal.",
        "operation": "Passive-tree or jewel operation to propose.",
        "nodeId": "Passive node identifier for the proposed operation.",
        "socketNodeId": "Jewel socket node identifier for the proposed operation.",
    }
    return descriptions.get(field, f"{field} value used by {name}.")


def _schema(record: dict) -> dict:
    name = record["name"]
    props = {key: {**_json_type(kind), "description": _field_description(name, key)}
             for key, kind in record["arguments"].items()}
    if "source" in props: props["source"]["enum"] = ["poedb", "poewiki", "both"]
    if name == "search_external": props["limit"].update({"minimum": 1, "maximum": 3})
    if name == "search_external": props["query"]["maxLength"] = 200
    if name == "search_knowledge": props["limit"]["minimum"] = 1
    if "skillIndex" in props: props["skillIndex"]["minimum"] = 1
    if "itemId" in props: props["itemId"]["minimum"] = 1
    if "level" in props: props["level"].update({"minimum": 1, "maximum": 40})
    if "quality" in props: props["quality"].update({"minimum": 0, "maximum": 100})
    if "comparisonFields" in props: props["comparisonFields"]["items"] = {"type": "string"}
    if name == "search_knowledge": props["limit"]["default"] = 10
    if name == "search_external":
        props["limit"]["default"] = 3
        props["source"]["default"] = "both"
    result = {"type":"object", "properties":props, "additionalProperties":False}
    if record["required"]: result["required"] = list(record["required"])
    if "skillIndex" in props and "skillName" in props: result["anyOf"] = [{"required":["skillIndex"]},{"required":["skillName"]}]
    return result

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    group: str
    arguments: dict
    required: tuple
    input_schema: dict
    category: str
    purpose: str
    when_to_use: str
    constraints: str
    returns: str
    side_effect: str
    idempotent: bool
    open_world: bool
    timeout_seconds: int
    retry_policy: str
    error_codes: tuple
    examples: tuple

    def as_mcp_definition(self) -> dict:
        return {"name": self.name, "description": self.description, "inputSchema": self.input_schema,
                "annotations": {"readOnlyHint": self.side_effect == "read_only",
                                "destructiveHint": False,
                                "idempotentHint": self.idempotent,
                                "openWorldHint": self.open_world}}

_CONTEXT_TOOLS = {"resolve_skill_context", "get_skill_chain", "get_socket_order", "get_curse_application_order", "get_support_links"}
_TRACE_TOOLS = {"get_skill_breakdown", "get_damage_breakdown", "explain_stat"}
_COMPARE_TOOLS = {"compare_build_states", "compare_support_effect", "explain_damage_change"}
_STATE_TOOLS = {"get_item_modifiers"}
_KNOWLEDGE_TOOLS = {"search_knowledge", "search_external", "resolve_item_alias", "resolve_skill_alias"}
_MUTATION_TOOLS = {"replace_item", "replace_gem", "change_passive"}


def _category(name):
    if name in _KNOWLEDGE_TOOLS: return "knowledge_search"
    if name in _MUTATION_TOOLS: return "mutation"
    if name in _CONTEXT_TOOLS: return "context_resolution"
    if name in _TRACE_TOOLS: return "trace_evidence"
    if name in _COMPARE_TOOLS: return "comparison_simulation"
    if name in _STATE_TOOLS: return "state_metadata"
    return "calculation"


def _example(record, schema):
    required = list(record["required"])
    alternatives = schema.get("anyOf", ())
    if alternatives and not any(set(candidate.get("required", ())) <= set(required) for candidate in alternatives):
        required.extend(alternatives[0].get("required", ()))
    arguments = {}
    for key in required:
        field = schema["properties"][key]
        if "default" in field:
            value = field["default"]
        elif "enum" in field:
            value = field["enum"][0]
        else:
            kind = field.get("type")
            if kind is None and field.get("anyOf"):
                kind = field["anyOf"][0].get("type")
            value = {"integer": max(1, field.get("minimum", 1)), "boolean": True,
                     "object": {}, "array": [], "string": key + " example"}.get(kind, "example")
            if key == "durationType": value = "duration"
            if key == "itemText": value = "Rarity: Normal\\nExample Item"
            if key == "slot": value = "Weapon 1"
        arguments[key] = value
    return {"tool": record["name"], "arguments": arguments}


def _make_spec(record):
    name, group = record["name"], record["group"]
    category = _category(name)
    side_effect = "mutation_request" if category == "mutation" else "read_only"
    purpose = record["description"]
    when = ("Use when external or indexed PoE knowledge is needed." if category == "knowledge_search"
            else "Use after identifying the relevant active build, skill, or snapshot context." if category in {"context_resolution", "trace_evidence", "comparison_simulation"}
            else "Use to inspect the active PoB calculation or build state.")
    constraints = "Only the declared arguments are accepted; live mutation is capability-gated." if side_effect != "read_only" else "Read-only and scoped to the supplied arguments and current PoB context."
    returns = "Common result envelope with facts, provenance, and evidence when available."
    description = f"{purpose} {when} Constraints: {constraints} Returns: {returns}"
    codes = ["INPUT_INVALID", "TOOL_NOT_FOUND", "UNCLASSIFIED_FAILURE"]
    if group == "pob_live": codes.extend(["VALUE_UNAVAILABLE", "TIMEOUT", "TOOL_TRANSIENT", "BRIDGE_PROTOCOL_ERROR"])
    if group == "snapshot_compare": codes.extend(["INPUT_INVALID", "VALUE_UNAVAILABLE", "TIMEOUT", "TOOL_TRANSIENT"])
    if group == "knowledge": codes.extend(["RAG_UNAVAILABLE", "RAG_TRANSIENT", "TOOL_TRANSIENT"])
    if group == "external_search": codes.extend(["SEARCH_TRANSIENT", "TOOL_TRANSIENT", "VALUE_UNAVAILABLE", "TIMEOUT"])
    if group == "mutation": codes.append("MUTATION_NOT_PERSISTENT")
    schema = _schema(record)
    return ToolSpec(name, description, group, record["arguments"], tuple(record["required"]), schema,
                    category, purpose, when, constraints, returns, side_effect,
                    side_effect == "read_only", group == "external_search",
                    45 if group in {"external_search", "pob_live", "snapshot_compare"} else 10,
                    "never" if side_effect != "read_only" else "transient_read_only",
                    tuple(dict.fromkeys(codes)),
                    (__import__("json").dumps(_example(record, schema), ensure_ascii=False),))


TOOL_CATALOG = {record["name"]: _make_spec(record) for record in _TOOL_RECORDS}
ALLOWED_TOOLS = frozenset(TOOL_CATALOG)
