# Tool Catalog

All Tools are invoked with structured JSON and execute locally through the PoB Bridge. The listed output paths are PoB paths, not independently calculated replacements. `implemented/public` below means the Tool is present in the current Agent allowlist/handler registration and has an exported implementation.

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

## Implemented comparison Tools

| Tool | Main arguments | Result |
|---|---|---|
| `compare_support_effect` | Skill Set, skill, support | PoB-calculated before/after support facts |
| `explain_damage_change` | Skill Set, skill, support | change facts, delta, and evidence trace |
`compare_support_effect` and `explain_damage_change` compare PoB-calculated support states. No current public Tool mutates the build.

## Planned Tools

The following are product requirements but are not currently implemented or publicly registered:

| Tool | Planned arguments | Planned behavior |
|---|---|---|
| `compare_build_states` | two local build states and skill indexes | compare already-calculated outputs and return before/after/delta |
| `replace_item` | slot, copied item text | mutate current in-memory item and recalculate |
| `replace_gem` | socket group, gem identity, level, quality | mutate current in-memory gem and recalculate |
| `change_passive` | node or cluster-jewel operation | mutate current tree and recalculate |

These planned Tools must follow revision checks, preserve user UI changes, return the common envelope, and never save files automatically.

Mutation Tools never save files. They fail on revision conflicts and preserve the user's newer UI state.
