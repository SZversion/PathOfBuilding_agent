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

## Not yet proven by direct source comparison

- The complete `increased`/`more`/`less` calculation order
- Added damage, Gain as Extra, and conversion ordering in every damage path
- Resistance reduction, Exposure, curse reduction, and penetration ordering
- Full skill-tag semantics and every proxy ownership exception
- Armour formula and all defense interaction layers
- Hex/Mark application and curse replacement order
- Full ailment application, duration, magnitude, and damage formulas
- Projectile Chain/Fork/Pierce/Split and single-target overlap behavior

These rules remain `needs_patch_check` and require focused comparison against the relevant PoB calculation modules plus patch-specific test cases.

