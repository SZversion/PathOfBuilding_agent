# Tool Catalog

All Tools are invoked with structured JSON and execute locally through the PoB Bridge. The listed output paths are PoB paths, not independently calculated replacements. `implemented/public` below means the Tool is present in the current Agent allowlist/handler registration and has an exported implementation.

Mutation adapter boundary: the current Python bridge launches a one-shot headless PoB process per request. Therefore mutation Tools are exposed as a headless adapter contract only and are not live-session persistent by default (`MUTATION_NOT_PERSISTENT`). They may be promoted to live public mutation only after an in-process PoB session preserves the authoritative UI state across calls; Save/Save As remains user-controlled.

## Public Tool description contract

Every `implemented/public` row is required to have these seven description fields in its detailed specification (the summary tables below remain the registry): `What`, `When`, `How`, `Output`, `Constraints`, `sideEffect`, and `riskLevel`. `sideEffect` is `none` for all currently public read-only Tools; `riskLevel` is `low` unless a Tool can mutate state. The catalog linter verifies that every public name is present in both the planner allowlist and Bridge handler registry and that this contract is documented before promotion.

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
- `replace_item`: What=replace equipped item; When=user explicitly requests an item swap; How=headless PoB adapter transaction; Output=before/after metadata and output delta; Constraints=registered contract, disabled by default for live UI, valid slot/item text, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium
- `replace_gem`: What=replace a socketed gem; When=user explicitly requests a gem swap; How=headless PoB adapter transaction and recalculation; Output=before/after gem facts, link facts, output delta, and evidence graph; Constraints=registered contract, headless adapter only until persistent session exists, socket group/index, level/quality, variant/support compatibility, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium
- `change_passive`: What=change passive allocation or cluster jewel; When=user explicitly requests a tree change; How=headless PoB PassiveSpec adapter; Output=before/after tree, output delta, and evidence graph; Constraints=registered contract, disabled by default for live UI, valid path, prerequisites, points, socket/item, stale/idempotency checks, never saves; sideEffect=in_memory; riskLevel=medium

## Implemented and public

| Tool | Main arguments | PoB output/breakdown basis |
|---|---|---|
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
| `replace_item` | slot, itemIdentity, itemText, expectedSnapshotRevision, idempotencyKey, fingerprint | **Headless adapter only; disabled by default for live UI** |
| `replace_gem` | socketGroup, gemIdentity, level, quality, enabled, expectedSnapshotRevision, idempotencyKey, fingerprint | **Headless adapter only; disabled by default for live UI** |
| `change_passive` | operation, nodeId/socketNodeId, itemId, expectedSnapshotRevision, idempotencyKey, fingerprint | **Headless adapter only; disabled by default for live UI** |
`compare_support_effect` and `explain_damage_change` compare PoB-calculated support states. Mutation Tools are registered contracts, but the current one-shot bridge exposes them only through the headless adapter and returns `MUTATION_NOT_PERSISTENT` unless explicitly enabled. They never invoke Save/Save As.

## Planned Tools

The following are product requirements but are not currently implemented or publicly registered:

| Tool | Planned arguments | Planned behavior |
|---|---|---|

These planned Tools must follow revision checks, preserve user UI changes, return the common envelope, and never save files automatically.

Mutation Tools never save files. They fail on revision conflicts and preserve the user's newer UI state.
