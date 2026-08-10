# PoE 1 Rule Validation Report

Validation target: current PoB source tree on branch `feat/pob-agent-architecture`.

## Confirmed in PoB source

| Rule or fact | PoB evidence | Result |
|---|---|---|
| Campaign penalty options | `src/Modules/ConfigOptions.lua:135` exposes `0`, `-30` (Act 5), and `-60` (Act 10) | Confirmed as PoB configuration options |
| Curse limit default | `src/Modules/CalcSetup.lua:530` creates `EnemyCurseLimit` with base `1` | Confirmed |
| Default projectile count | `src/Modules/CalcSetup.lua:532` creates `ProjectileCount` with base `1` | Confirmed |
| Default maximum resistance | `src/Modules/Data.lua:243` defines `base_maximum_all_resistances_%` as `75`; `CalcSetup.lua:19-22` applies it to player and totem resistance caps | Confirmed |
| Spell Suppression | `src/Modules/Data.lua:243-244` defines a 100% chance cap and 40% default suppression effect; `CalcDefence.lua:1128-1129` consumes both values | Confirmed |
| Player base Evasion | `src/Data/Misc.lua:83` defines `base_evasion_rating = 15` | Confirmed |
| Player critical multiplier | `src/Data/Misc.lua:88-89` defines 150 base critical multiplier and +50 ailment DoT multiplier for critical strikes | Confirmed |
| Active Brand limit | `src/Modules/CalcSetup.lua:529` creates `ActiveBrandLimit` with base `3` | Confirmed |

## Important discrepancy

`src/Modules/CalcSetup.lua:503-506` applies the selected `resistancePenalty` to **Fire, Cold, Lightning, and Chaos Resistance**. The current knowledge rule describes the campaign penalty only for elemental resistances.

This means the PoB implementation and the live-game rule must be represented separately until the scope is confirmed for the target PoE 1 patch. Do not use the current campaign rule to infer Chaos Resistance from PoB without checking the build's actual PoB output.

## Results for the previously unproven items

The direct source comparison is now recorded in `poe1-pob-validation.json`. The statuses below deliberately distinguish a PoB implementation finding from a complete universal game-rule claim.

| Item | Status | PoB evidence | Interpretation |
|---|---|---|---|
| Increased/decreased aggregation | Confirmed | `src/Classes/ModList.lua:97-116` | Matching modifiers are summed. |
| More/less operation and global order | Partial | `src/Classes/ModList.lua:118-147` | Multiplicative factors are confirmed; every stage's ordering is not. |
| Added damage | Partial | `src/Modules/CalcOffence.lua:1878-1945` | Separate damage tables exist, but the universal ordering claim needs fixtures. |
| Gain as Extra | Confirmed | `src/Modules/CalcOffence.lua:1878-1945` | Stored separately from conversion. |
| Conversion | Confirmed | `src/Modules/CalcOffence.lua:1878-1945` | Ordered damage-type conversion and >100% normalization are implemented. |
| Resistance reduction / Exposure / penetration ordering | Partial | `src/Modules/CalcOffence.lua:3466-3475`; `src/Modules/CalcPerform.lua:3572-3585` | Separate paths are present; complete ordering remains unproven. |
| Skill tags and scoped modifiers | Confirmed | `src/Data/Gems.lua`; `src/Modules/CalcOffence.lua:3536-3545` | Tags and skill flags gate calculations. |
| Proxy ownership exceptions | Not confirmed | `src/Data/Gems.lua`; `src/Modules/CalcPerform.lua` | Requires per-mechanic cases. |
| Armour formula | Confirmed | `src/Modules/CalcDefence.lua:111-121` | Effective armour uses the `armour / (armour + damage * 5)` mitigation form. |
| Hex/Mark and curse replacement | Partial | `src/Modules/CalcPerform.lua:2602-2637`; `3156-3246` | Limits, mark distinction, and replacement slots are implemented; exact game order needs fixtures. |
| Ailment application and damage | Partial | `src/Modules/CalcPerform.lua:836-865`; `3432-3539` | Avoidance/immunity/effect paths are present; all formulas are not covered. |
| Projectile secondary behavior and overlap | Not confirmed | `src/Modules/CalcOffence.lua:3536-3545` | Tagging is present, but Chain/Fork/Pierce/Split overlap needs dedicated tests. |

Rules updated from `needs_patch_check` to `verified` only where the PoB source directly proves the stated operation. Partial and unresolved claims remain conservative and are listed in the machine-readable validation file.

## Additional runtime systems validated

The second comparison pass added `poe1-runtime-rules.json`, covering resource calculation and reservation, standard charge limits, totem and trap limits, trigger-rate/cooldown behavior, leech pools, and on-hit recovery. Full proxy ownership remains intentionally unresolved because PoB branches by mechanic and skill metadata.

The third comparison pass added `poe1-buffs-flasks-attributes.json`, covering attribute-derived stats, Fortify, Onslaught, Tailwind, Elusive, flask effect/charges/recovery, level-based resources, monster-level scaling, and Guard Skill state.

The fourth comparison pass added `poe1-projectile-rules.json`, confirming the default projectile count, projectile skill gating, and separate trap/mine throwing calculations. Chain/Fork/Pierce/Split and single-target overlap remain fixture-dependent.

The fifth comparison pass added `poe1-map-monster-rules.json`, confirming representative map effects such as Hexproof, enemy resistance, monster Life, ailment avoidance, and gain-as-extra damage. The full map-modifier catalog remains data-driven and is not summarized as one universal rule.

The sixth comparison pass added `poe1-recoup-rules.json` and `poe1-progression-rules.json`. Recoup is now fully indexed from the damage simulation path, including resource conversion and duration. Experience penalties, act/level estimation, Labyrinth recommendations, and Ascendancy point validation are also indexed; the complete quest reward catalog remains a data-indexing task.
