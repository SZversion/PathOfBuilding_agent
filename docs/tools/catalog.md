# Tool Catalog

All Tools are invoked with structured JSON and execute locally through the PoB Bridge. The listed output paths are PoB paths, not independently calculated replacements. `implemented/public` below means the Tool is present in the current Agent allowlist/handler registration and has an exported implementation.

Mutation adapter boundary: mutation Tools remain registered but the MCP server returns `MUTATION_NOT_PERSISTENT`; it never calls the one-shot headless PoB bridge and never saves a build.

Production backend routing: all 32 registered tools are served by the local MCP stdio process. PoB read-only operations go through the authenticated live Lua endpoint; local knowledge and aliases use the bundled index; external lookup uses the approved HTTPS providers; snapshot comparison uses the supplied snapshots. The three mutation contracts remain discoverable and return `MUTATION_NOT_PERSISTENT` without calling the headless bridge.

## Public Tool description contract

Every `implemented/public` row is required to have these seven description fields in its detailed specification (the summary tables below remain the registry): `What`, `When`, `How`, `Output`, `Constraints`, `sideEffect`, and `riskLevel`. `sideEffect` is `none` for read-only Tools; `riskLevel` is `low` unless a Tool can mutate state. The linter verifies docs, the single-source Python catalog, and Lua PoB dispatch parity.

Extending the tool set: add one record to `agent/tool_catalog.py`, then implement the provider for its declared group. AgentLoop and MCP schemas/definitions derive from that record. For a new PoB tool, also add it to `src/Modules/AgentBridge.lua`'s read-only capability table and its Lua handler; `python tools/lint_agent_catalog.py` checks that boundary. Add one focused contract/dispatch test with the tool.

### Public Tool contracts

Each line is the minimum contract record; tool-specific PoB paths and arguments remain in the registry tables below.

- `compare_support_effect`: What=compare support; When=before/after support question; How=PoB comparison; Output=common envelope; Constraints=read-only and current snapshot; sideEffect=none; riskLevel=low
- `compare_build_states`: What=compare two local snapshots; When=before/after build comparison; How=compare PoB outputs; Output=before/after/delta/change-rate/changed-fields in common envelope; Constraints=version and skill validation, read-only, no file save; sideEffect=none; riskLevel=low
- `explain_damage_change`: What=explain damage delta; When=support comparison; How=PoB output and trace; Output=common envelope; Constraints=no independent formula; sideEffect=none; riskLevel=low
- `explain_stat`: What=explain stat; When=source question; How=PoB output and modifier trace; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_ailment_effect`: What=ailment values; When=ailment question; How=PoB output; Output=common envelope; Constraints=unavailable when absent; sideEffect=none; riskLevel=low
- `get_character_stats`: What=character stats; When=build stat question; How=PoB player output; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_conversion_chain`: What=damage conversion; When=conversion question; How=PoB conversion table; Output=common envelope; Constraints=no reimplementation; sideEffect=none; riskLevel=low
- `get_curse_application_order`: What=curse order; When=curse ordering question; How=socket order; Output=common envelope; Constraints=may be not_simulated; sideEffect=none; riskLevel=low
- `get_curse_limit`: What=curse limit; When=curse capacity question; How=PoB player output; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_damage_breakdown`: What=damage breakdown; When=damage source question; How=PoB breakdown; Output=common envelope; Constraints=raw precision; sideEffect=none; riskLevel=low
- `get_duration`: What=duration; When=duration question; How=PoB output and trace; Output=common envelope; Constraints=duration type required; sideEffect=none; riskLevel=low
- `get_effective_resistance`: What=effective resistance; When=resistance question; How=PoB output; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_elemental_penetration`: What=penetration; When=penetration question; How=PoB output; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_highest_dps_skill`: What=highest DPS skill; When=skill omitted; How=PoB output scan; Output=common envelope; Constraints=calculated skills only; sideEffect=none; riskLevel=low
- `get_item_modifiers`: What=item modifiers; When=item source question; How=PoB item data; Output=common envelope; Constraints=item id required; sideEffect=none; riskLevel=low
- `get_projectile_behavior`: What=projectile behavior; When=projectile question; How=PoB output; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `get_projectile_count`: What=projectile count; When=projectile count question; How=PoB output and trace; Output=common envelope; Constraints=no independent formula; sideEffect=none; riskLevel=low
- `get_skill_breakdown`: What=skill breakdown; When=calculation source question; How=PoB breakdown; Output=common envelope; Constraints=raw precision; sideEffect=none; riskLevel=low
- `get_skill_chain`: What=skill chain; When=chain question; How=PoB skill context; Output=common envelope; Constraints=skill identity required; sideEffect=none; riskLevel=low
- `get_skill_dps`: What=skill DPS; When=DPS question; How=PoB output; Output=common envelope; Constraints=skill index required; sideEffect=none; riskLevel=low
- `get_skill_stats`: What=skill stats; When=skill stat question; How=PoB skill output; Output=common envelope; Constraints=skill index required; sideEffect=none; riskLevel=low
- `get_socket_order`: What=socket order; When=link order question; How=PoB synthetic groups; Output=common envelope; Constraints=resolved skill required; sideEffect=none; riskLevel=low
- `get_support_links`: What=support links; When=link question; How=PoB socket group; Output=common envelope; Constraints=resolved skill required; sideEffect=none; riskLevel=low
- `get_trigger_sequence`: What=trigger metadata; When=trigger question; How=PoB skill metadata; Output=common envelope; Constraints=current snapshot; sideEffect=none; riskLevel=low
- `resolve_skill_context`: What=canonical skill context; When=skill alias question; How=alias and PoB resolution; Output=common envelope; Constraints=ambiguous alias asks user; sideEffect=none; riskLevel=low
- `search_external`: What=search PoE Wiki and PoEDB and fetch matching page bodies; When=local evidence is insufficient or an external reference is requested; How=Wiki MediaWiki API and PoEDB public autocomplete index plus direct page reads over HTTPS; Output=temporary results with page content, title, URL, source, and retrieval time; Constraints=approved domains only, read-only, session-only evidence, 3 results per source max, 12,000 content characters per page; sideEffect=none; riskLevel=low
- `search_knowledge`: What=search the local versioned PoE rules and mechanics index; When=a mechanic or rule needs project-curated evidence; How=rank indexed canonical documents; Output=matching documents and scores; Constraints=authoritative documents only by default; sideEffect=none; riskLevel=low
- `resolve_item_alias`: What=resolve a Korean or English item alias; When=an item name needs a canonical identity; How=exact alias match in the local index; Output=canonical item identity and localized names; Constraints=ambiguous matches are rejected; sideEffect=none; riskLevel=low
- `resolve_skill_alias`: What=resolve a Korean or English skill alias; When=a skill name needs a canonical gem identity; How=exact alias match in the local alias index; Output=gem and variant identity; Constraints=ambiguous matches are rejected; sideEffect=none; riskLevel=low
- `replace_item`: What=replace equipped item; When=user explicitly requests an item swap; How=headless PoB adapter transaction; Output=before/after metadata and output delta; Constraints=registered contract, disabled by default for live UI, valid slot/item text, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium
- `replace_gem`: What=replace a socketed gem; When=user explicitly requests a gem swap; How=headless PoB adapter transaction and recalculation; Output=before/after gem facts, link facts, output delta, and evidence graph; Constraints=registered contract, headless adapter only until persistent session exists, socket group/index, level/quality, variant/support compatibility, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium
- `change_passive`: What=change passive allocation or cluster jewel; When=user explicitly requests a tree change; How=headless PoB PassiveSpec adapter; Output=before/after tree, output delta, and evidence graph; Constraints=registered contract, disabled by default for live UI, valid path, prerequisites, points, socket/item, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium

## Implemented and public

| Tool | Main arguments | PoB output/breakdown basis |
|---|---|---|
| `search_external` | `query`, optional `source` (`poedb`/`poewiki`/`both`), `limit` (1–3; default 3) | PoE Wiki page API and PoEDB autocomplete index/page reads; page body as temporary external evidence |
| `search_knowledge` | `query`, optional `limit`, `category` | Local versioned knowledge index |
| `resolve_item_alias` | `query`, optional `category` | Exact Korean/English item alias index |
| `resolve_skill_alias` | `query` | Exact Korean/English skill alias index |
| `get_character_stats` | current build | `mainEnv.player.output` |
| `get_skill_stats` | `skillIndex` | `activeSkillList[skillIndex].output` and gem metadata |
| `get_skill_dps` | `skillIndex` | `activeSkillList[skillIndex].output.TotalDPS` |
| `get_highest_dps_skill` | current build | numeric `TotalDPS` scan |
| `get_skill_breakdown` | `skillIndex` | `activeSkillList[skillIndex].breakdown` |
| `explain_stat` | `stat`, optional `skillIndex` | output plus actor/skill modifier trace |
| `get_item_modifiers` | `itemId` | `itemsTab.items[itemId].*ModLines` |
| `get_projectile_count` | `skillIndex` | `output.ProjectileCount` |
| `get_projectile_behavior` | `skillIndex` | ProjectileCount, PierceCount, Chain, ChainMax, ForkCount, SplitCount |
| `get_skill_chain` | Skill Set selector, skill name | selected active skill output Chain fields |
| `get_duration` | `skillIndex`, `durationType` | Duration output and breakdown; Trauma path when available |
| `get_elemental_penetration` | `skillIndex` | `output.ElementalPenetration` |
| `get_effective_resistance` | `skillIndex` | `*EffMult` output fields |
| `get_curse_limit` | current build | `player.output.EnemyCurseLimit` |
| `get_ailment_effect` | `skillIndex` | calculated ailment/chance output keys |
| `get_conversion_chain` | `skillIndex` | `skill.conversionTable` |
| `get_support_links` | Skill Set selector, skill name | PoB socket/display gem order |
| `get_socket_order` | Skill Set selector, skill name | synthetic socket group order |
| `get_trigger_sequence` | `skillIndex` | `infoTrigger` and triggered metadata |
| `get_curse_application_order` | Skill Set selector, skill name | socket order only; may be `not_simulated` |
| `get_damage_breakdown` | `skillIndex` | active skill breakdown values |
| `resolve_skill_context` | Skill Set selector, skill name | canonical PoB skill context |

## Implemented comparison Tools

| Tool | Main arguments | Result |
|---|---|---|
| `compare_build_states` | beforeState, afterState, skillIndex, comparisonFields | read-only before/after/delta comparison with conditions and evidence |
| `compare_support_effect` | Skill Set, skill, support | PoB-calculated before/after support facts |
| `explain_damage_change` | Skill Set, skill, support | change facts, delta, and evidence trace |

## Implemented mutation Tools

| Tool | Main arguments | Result |
|---|---|---|
| `replace_item` | slot, itemIdentity, itemText, expectedSnapshotRevision, idempotencyKey, fingerprint | **MCP returns `MUTATION_NOT_PERSISTENT`; no adapter call** |
| `replace_gem` | socketGroup, gemIdentity, level, quality, enabled, expectedSnapshotRevision, idempotencyKey, fingerprint | **MCP returns `MUTATION_NOT_PERSISTENT`; no adapter call** |
| `change_passive` | operation, nodeId/socketNodeId, itemId, expectedSnapshotRevision, idempotencyKey, fingerprint | **MCP returns `MUTATION_NOT_PERSISTENT`; no adapter call** |
`compare_support_effect` and `explain_damage_change` compare PoB-calculated support states. Mutation Tools are registered contracts, but the MCP implementation rejects them with `MUTATION_NOT_PERSISTENT` before any bridge call. They never invoke Save/Save As.

## Planned Tools

The following are product requirements but are not currently implemented or publicly registered:

| Tool | Planned arguments | Planned behavior |
|---|---|---|

These planned Tools must follow revision checks, preserve user UI changes, return the common envelope, and never save files automatically.

Mutation Tools never save files. They fail on revision conflicts and preserve the user's newer UI state.

<!-- MCP TOOL CONTRACTS START -->
## Generated MCP contracts

These executable schemas are generated from `agent/tool_catalog.py`.

### `change_passive`

- Category: `mutation`; provider: `mutation`
- Purpose: Request a passive or jewel change; live execution is currently capability-gated.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Only the declared arguments are accepted; live mutation is capability-gated.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `mutation_request`; idempotent: `false`; timeout: 10s
- Retry: `never`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `MUTATION_NOT_PERSISTENT`
- Example: `{"tool": "change_passive", "arguments": {"operation": "operation example", "expectedSnapshotRevision": "expectedSnapshotRevision example", "idempotencyKey": "idempotencyKey example", "fingerprint": "fingerprint example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "description": "Passive-tree or jewel operation to propose."
    },
    "nodeId": {
      "type": "integer",
      "description": "Passive node identifier for the proposed operation."
    },
    "socketNodeId": {
      "type": "integer",
      "description": "Jewel socket node identifier for the proposed operation."
    },
    "itemId": {
      "type": "integer",
      "description": "PoB item identifier from the current build snapshot.",
      "minimum": 1
    },
    "expectedSnapshotRevision": {
      "type": "string",
      "description": "Snapshot revision the proposal was based on."
    },
    "idempotencyKey": {
      "type": "string",
      "description": "Caller-generated key identifying this mutation request."
    },
    "fingerprint": {
      "type": "string",
      "description": "Build or target fingerprint used to validate the proposal."
    }
  },
  "additionalProperties": false,
  "required": [
    "operation",
    "expectedSnapshotRevision",
    "idempotencyKey",
    "fingerprint"
  ]
}
```

### `compare_build_states`

- Category: `comparison_simulation`; provider: `snapshot_compare`
- Purpose: Compare two supplied PoB snapshots and report output deltas.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`
- Example: `{"tool": "compare_build_states", "arguments": {"beforeState": {}, "afterState": {}, "skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "beforeState": {
      "anyOf": [
        {
          "type": "object"
        },
        {
          "type": "string"
        }
      ],
      "description": "First normalized PoB snapshot or its serialized representation."
    },
    "afterState": {
      "anyOf": [
        {
          "type": "object"
        },
        {
          "type": "string"
        }
      ],
      "description": "Second normalized PoB snapshot or its serialized representation."
    },
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "comparisonFields": {
      "type": "array",
      "description": "Optional output fields to include in the comparison.",
      "items": {
        "type": "string"
      }
    }
  },
  "additionalProperties": false,
  "required": [
    "beforeState",
    "afterState",
    "skillIndex"
  ]
}
```

### `compare_support_effect`

- Category: `comparison_simulation`; provider: `pob_live`
- Purpose: Compare PoB-calculated outputs with and without a support gem.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "compare_support_effect", "arguments": {"skillName": "skillName example", "supportName": "supportName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "supportName": {
      "type": "string",
      "description": "Support gem name to evaluate against the selected skill."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName",
    "supportName"
  ]
}
```

### `explain_damage_change`

- Category: `comparison_simulation`; provider: `pob_live`
- Purpose: Return PoB calculation evidence for a support-related damage change.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "explain_damage_change", "arguments": {"skillName": "skillName example", "supportName": "supportName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "supportName": {
      "type": "string",
      "description": "Support gem name to evaluate against the selected skill."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName",
    "supportName"
  ]
}
```

### `explain_stat`

- Category: `trace_evidence`; provider: `pob_live`
- Purpose: Read a stat value and the PoB modifier trace supporting it.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "explain_stat", "arguments": {"stat": "stat example", "skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "stat": {
      "type": "string",
      "description": "PoB stat identifier or supported stat name to trace."
    },
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "required": [
    "stat"
  ],
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_ailment_effect`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read calculated ailment values and chances for a skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_ailment_effect", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_character_stats`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read character statistics calculated by the active Path of Building session.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_character_stats", "arguments": {}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

### `get_conversion_chain`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read PoB's damage conversion and gain chain for a skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_conversion_chain", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_curse_application_order`

- Category: `context_resolution`; provider: `pob_live`
- Purpose: Read socket order relevant to curse application; does not simulate timing.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_curse_application_order", "arguments": {"skillName": "skillName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName"
  ]
}
```

### `get_curse_limit`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read the active build's calculated curse limit.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_curse_limit", "arguments": {}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

### `get_damage_breakdown`

- Category: `trace_evidence`; provider: `pob_live`
- Purpose: Read PoB's damage breakdown for a selected skill.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_damage_breakdown", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_duration`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read a selected skill duration and its PoB breakdown.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_duration", "arguments": {"durationType": "duration", "skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "durationType": {
      "type": "string",
      "description": "Duration field to explain, such as skill or debuff duration."
    }
  },
  "additionalProperties": false,
  "required": [
    "durationType"
  ],
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_effective_resistance`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read PoB's effective resistance multipliers.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_effective_resistance", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_elemental_penetration`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read calculated elemental penetration for a skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_elemental_penetration", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_highest_dps_skill`

- Category: `calculation`; provider: `pob_live`
- Purpose: Find the active skill with the highest calculated PoB DPS.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_highest_dps_skill", "arguments": {}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

### `get_item_modifiers`

- Category: `state_metadata`; provider: `pob_live`
- Purpose: Read modifier lines from an item in the active build.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_item_modifiers", "arguments": {"itemId": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "itemId": {
      "type": "integer",
      "description": "PoB item identifier from the current build snapshot.",
      "minimum": 1
    }
  },
  "additionalProperties": false,
  "required": [
    "itemId"
  ]
}
```

### `get_projectile_behavior`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read projectile count, pierce, chain, fork, and split outputs.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_projectile_behavior", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_projectile_count`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read PoB's calculated projectile count for a skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_projectile_count", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_skill_breakdown`

- Category: `trace_evidence`; provider: `pob_live`
- Purpose: Read PoB's calculation breakdown for a selected skill.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_skill_breakdown", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_skill_chain`

- Category: `context_resolution`; provider: `pob_live`
- Purpose: Read chain values for a skill in a selected Skill Set.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_skill_chain", "arguments": {"skillName": "skillName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName"
  ]
}
```

### `get_skill_dps`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read PoB's calculated DPS for a selected skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_skill_dps", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_skill_stats`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read calculated output and gem metadata for a selected skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_skill_stats", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `get_socket_order`

- Category: `context_resolution`; provider: `pob_live`
- Purpose: Read PoB's socket and synthetic group order for a skill.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_socket_order", "arguments": {"skillName": "skillName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName"
  ]
}
```

### `get_support_links`

- Category: `context_resolution`; provider: `pob_live`
- Purpose: Read the active support links for a selected skill.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_support_links", "arguments": {"skillName": "skillName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName"
  ]
}
```

### `get_trigger_sequence`

- Category: `calculation`; provider: `pob_live`
- Purpose: Read trigger metadata and sequence fields for a skill.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "get_trigger_sequence", "arguments": {"skillIndex": 1}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillIndex": {
      "type": "integer",
      "description": "One-based skill index in the selected Skill Set.",
      "minimum": 1
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    },
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    }
  },
  "additionalProperties": false,
  "anyOf": [
    {
      "required": [
        "skillIndex"
      ]
    },
    {
      "required": [
        "skillName"
      ]
    }
  ]
}
```

### `replace_gem`

- Category: `mutation`; provider: `mutation`
- Purpose: Request a gem replacement; live execution is currently capability-gated.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Only the declared arguments are accepted; live mutation is capability-gated.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `mutation_request`; idempotent: `false`; timeout: 10s
- Retry: `never`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `MUTATION_NOT_PERSISTENT`
- Example: `{"tool": "replace_gem", "arguments": {"socketGroup": 1, "gemIdentity": "gemIdentity example", "level": 1, "quality": 1, "expectedSnapshotRevision": "expectedSnapshotRevision example", "idempotencyKey": "idempotencyKey example", "fingerprint": "fingerprint example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "socketGroup": {
      "anyOf": [
        {
          "type": "integer"
        },
        {
          "type": "string"
        }
      ],
      "description": "Socket group index or supported group selector."
    },
    "gemIdentity": {
      "type": "string",
      "description": "Canonical identity of the proposed gem."
    },
    "level": {
      "type": "integer",
      "description": "Gem level for the proposed change.",
      "minimum": 1,
      "maximum": 40
    },
    "quality": {
      "type": "integer",
      "description": "Gem quality for the proposed change.",
      "minimum": 0,
      "maximum": 100
    },
    "enabled": {
      "type": "boolean",
      "description": "Whether the gem should be enabled in the proposal."
    },
    "expectedSnapshotRevision": {
      "type": "string",
      "description": "Snapshot revision the proposal was based on."
    },
    "idempotencyKey": {
      "type": "string",
      "description": "Caller-generated key identifying this mutation request."
    },
    "fingerprint": {
      "type": "string",
      "description": "Build or target fingerprint used to validate the proposal."
    }
  },
  "additionalProperties": false,
  "required": [
    "socketGroup",
    "gemIdentity",
    "level",
    "quality",
    "expectedSnapshotRevision",
    "idempotencyKey",
    "fingerprint"
  ]
}
```

### `replace_item`

- Category: `mutation`; provider: `mutation`
- Purpose: Request an item replacement; live execution is currently capability-gated.
- When: Use to inspect the active PoB calculation or build state.
- Constraints: Only the declared arguments are accepted; live mutation is capability-gated.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `mutation_request`; idempotent: `false`; timeout: 10s
- Retry: `never`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `MUTATION_NOT_PERSISTENT`
- Example: `{"tool": "replace_item", "arguments": {"slot": "Weapon 1", "itemIdentity": "itemIdentity example", "itemText": "Rarity: Normal\\nExample Item", "expectedSnapshotRevision": "expectedSnapshotRevision example", "idempotencyKey": "idempotencyKey example", "fingerprint": "fingerprint example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "slot": {
      "type": "string",
      "description": "Equipment slot to target in the proposed replacement."
    },
    "itemIdentity": {
      "type": "string",
      "description": "Canonical identity of the proposed item."
    },
    "itemText": {
      "type": "string",
      "description": "Serialized item text for the proposed replacement."
    },
    "expectedSnapshotRevision": {
      "type": "string",
      "description": "Snapshot revision the proposal was based on."
    },
    "idempotencyKey": {
      "type": "string",
      "description": "Caller-generated key identifying this mutation request."
    },
    "fingerprint": {
      "type": "string",
      "description": "Build or target fingerprint used to validate the proposal."
    }
  },
  "additionalProperties": false,
  "required": [
    "slot",
    "itemIdentity",
    "itemText",
    "expectedSnapshotRevision",
    "idempotencyKey",
    "fingerprint"
  ]
}
```

### `resolve_item_alias`

- Category: `knowledge_search`; provider: `knowledge`
- Purpose: Resolve an exact Korean or English item alias to its canonical identity.
- When: Use when external or indexed PoE knowledge is needed.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 10s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `RAG_UNAVAILABLE`, `RAG_TRANSIENT`, `TOOL_TRANSIENT`
- Example: `{"tool": "resolve_item_alias", "arguments": {"query": "query example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Item, skill, mechanic, or page text to look up."
    },
    "category": {
      "type": "string",
      "description": "Optional knowledge category used to narrow the lookup."
    }
  },
  "additionalProperties": false,
  "required": [
    "query"
  ]
}
```

### `resolve_skill_alias`

- Category: `knowledge_search`; provider: `knowledge`
- Purpose: Resolve an exact Korean or English skill alias to its canonical gem identity.
- When: Use when external or indexed PoE knowledge is needed.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 10s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `RAG_UNAVAILABLE`, `RAG_TRANSIENT`, `TOOL_TRANSIENT`
- Example: `{"tool": "resolve_skill_alias", "arguments": {"query": "query example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Item, skill, mechanic, or page text to look up."
    }
  },
  "additionalProperties": false,
  "required": [
    "query"
  ]
}
```

### `resolve_skill_context`

- Category: `context_resolution`; provider: `pob_live`
- Purpose: Resolve a skill name to its active PoB skill context.
- When: Use after identifying the relevant active build, skill, or snapshot context.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `VALUE_UNAVAILABLE`, `TIMEOUT`, `TOOL_TRANSIENT`, `BRIDGE_PROTOCOL_ERROR`
- Example: `{"tool": "resolve_skill_context", "arguments": {"skillName": "skillName example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "skillSetSelector": {
      "type": "string",
      "description": "Optional Skill Set selector; defaults to the active set."
    },
    "skillName": {
      "type": "string",
      "description": "Skill name used to resolve the active skill context."
    }
  },
  "additionalProperties": false,
  "required": [
    "skillName"
  ]
}
```

### `search_external`

- Category: `knowledge_search`; provider: `external_search`
- Purpose: Search PoE Wiki and PoEDB and return matching page bodies with source URLs.
- When: Use when external or indexed PoE knowledge is needed.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 45s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `SEARCH_TRANSIENT`, `TOOL_TRANSIENT`, `VALUE_UNAVAILABLE`, `TIMEOUT`
- Example: `{"tool": "search_external", "arguments": {"query": "query example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Item, skill, mechanic, or page text to look up.",
      "maxLength": 200
    },
    "source": {
      "type": "string",
      "description": "External source selection: PoEDB, PoE Wiki, or both.",
      "enum": [
        "poedb",
        "poewiki",
        "both"
      ],
      "default": "both"
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of results to return.",
      "minimum": 1,
      "maximum": 3,
      "default": 3
    }
  },
  "additionalProperties": false,
  "required": [
    "query"
  ]
}
```

### `search_knowledge`

- Category: `knowledge_search`; provider: `knowledge`
- Purpose: Search the local versioned Path of Exile rules and mechanics knowledge base.
- When: Use when external or indexed PoE knowledge is needed.
- Constraints: Read-only and scoped to the supplied arguments and current PoB context.
- Returns: Common result envelope with facts, provenance, and evidence when available.
- Side effect: `read_only`; idempotent: `true`; timeout: 10s
- Retry: `transient_read_only`; errors: `INPUT_INVALID`, `TOOL_NOT_FOUND`, `UNCLASSIFIED_FAILURE`, `RAG_UNAVAILABLE`, `RAG_TRANSIENT`, `TOOL_TRANSIENT`
- Example: `{"tool": "search_knowledge", "arguments": {"query": "query example"}}`
- Input schema:

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Item, skill, mechanic, or page text to look up."
    },
    "limit": {
      "type": "integer",
      "description": "Maximum number of results to return.",
      "minimum": 1,
      "default": 10
    },
    "category": {
      "type": "string",
      "description": "Optional knowledge category used to narrow the lookup."
    }
  },
  "additionalProperties": false,
  "required": [
    "query"
  ]
}
```
<!-- MCP TOOL CONTRACTS END -->
