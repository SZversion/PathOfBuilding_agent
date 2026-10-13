---
name: compare
description: Use for requested item, gem, passive, set, or Config changes; before/after comparisons; and comparisons between builds including numeric differences and their supported causes.
---

# Changes and comparisons

## Establish the compared states

Use the current snapshot as the baseline unless the user names another build or state. Resolve explicitly requested targets from the supplied catalogs and context. Preserve each side's build identity, revision, selected tree/spec, Skill Set, Item Set, Config Set, main skill, and calculation conditions.
If a required target is absent, first use an available Tool that can retrieve it. Ask only for information that cannot be retrieved through available Tools. Do not treat a failed Tool call as a missing retrieval capability.
For a requested single change, keep other conditions equal. For different builds, identify relevant differences in skills, boss tier, buffs, charges, enabled state, and other Config conditions. Do not silently normalize conditions or compare different DPS definitions as the same measure. Explain when like-for-like comparison is unavailable.

## Obtain authoritative results

Use the actual Tool descriptions and schemas. compare_build_states requires beforeState, afterState, and skillIndex; resolve the index from the supplied skill data rather than inventing it. The states contain already-calculated PoB outputs; the Tool compares numeric scalar keys and returns before, after, and delta. It does not open arbitrary build files or calculate an unprovided build. Retrieve or calculate both states using available Tools before comparing them.
Use compare_support_effect or explain_damage_change when their documented inputs and purpose match the requested comparison. Do not estimate PoB results from item text, gem descriptions, or model knowledge.
A comparison request uses temporary calculation conditions and must not be presented as a persisted change. A change request requires a supported execution Tool and confirmation from its returned result. The current planner excludes mutation Tools; do not plan replace_item, replace_gem, or change_passive or claim that a change was applied. Explain unsupported operations accurately. Save and Save As remain user actions.

## Request-specific selectors and Config

Use contextOverrides for explicitly requested activeSpec, activeSkillSet, activeItemSet, and activeConfigSet, resolving IDs from the supplied catalogs. Use skillName for an explicit skill and configOverrides for explicit calculation conditions, only where the Tool accepts them. Do not include unmentioned Config fields.
Use exact PoB Config values:

- enemyIsBoss: None, Boss, Pinnacle, or Uber.
- resistancePenalty: 0, -30, or -60.
- Boolean fields: conditionMoving, conditionFullLife, conditionLowLife, conditionFullMana, conditionLowMana, conditionFullEnergyShield, conditionLowEnergyShield, conditionHaveEnergyShield, conditionUnbrokenWard, conditionEnemyCursed, conditionEnemyBleeding, conditionEnemyPoisoned, conditionEnemyBurning, conditionEnemyIgnited, conditionEnemyChilled, conditionEnemyFrozen, conditionEnemyShocked, usePowerCharges, useFrenzyCharges, useEnduranceCharges.
- Nonnegative integer fields: conditionStationary, overridePowerCharges, overrideFrenzyCharges, overrideEnduranceCharges.

Never invent Config values or unsupported fields. Report temporary conditions separately from settings actually applied.

## Explain where and how much the builds differ

For a general build comparison, cover available relevant values in these groups:

- Offence: comparable skill DPS, critical strike chance and multiplier, attack/cast speed, and other relevant damage outputs.
- Defence: life, energy shield, resistances, armour, evasion, maximum hit taken, and other exposed defensive outputs.
- Resources: mana, reservation, regeneration, cost, and other exposed resource outputs.
- Composition: active skills and supports, gem levels/qualities, items, allocated passives, selected sets, and Config differences.

For each reported numeric difference, identify the exact metric and show baseline value, comparison value, signed delta, and units. Show relative change as (after - before) / before * 100 only when the baseline is nonzero and the metric supports that interpretation. A zero baseline has no defined percentage change; do not report infinity or invent a percentage. For percentage-valued metrics, report the absolute change in percentage points: critical chance 40% to 50% is +10 percentage points. DPS 1,000,000 to 1,200,000 is +200,000 (+20%).
Prioritize the user's named metrics, then material gains and losses. State unavailable metrics rather than inventing values. A scalar comparison Tool does not by itself establish item, gem, passive, or Config differences; obtain those from supplied state data or other supported Tools.

## Explain causes using evidence

Connect numeric differences to demonstrated item, gem, passive, and condition differences using PoB breakdowns, modifier sources, or supported comparison evidence. Separate observed composition differences from established causal contributions.
When multiple components changed, do not assign a precise contribution to each component without controlled individual-change results or equivalent PoB evidence. If that evidence cannot be obtained, describe the total difference and plausible associations as inference without claiming an exact cause. Do not add unrelated experiments beyond the requested scope.
Finish when the requested comparison and available evidence, or the actual supported change result, have been reported. Clearly distinguish comparison-only results, applied changes, partial results, and unsupported operations.
