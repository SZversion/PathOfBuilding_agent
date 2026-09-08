# Rule Validation Workflow

This workflow validates English canonical PoE1 rules and the evidence used by the Agent. It is designed for the latest supported game version while preserving uncertainty and historical context.

## 1. Validation state machine

Canonical verification moves through these states:

```text
draft
  → source_checked
  → pob_checked
  → fixture_verified
  → regression_locked
```

- `draft`: authored but not safe as sole final-answer evidence.
- `source_checked`: source metadata, attribution, retrieval time, version applicability, and statement scope have been reviewed.
- `pob_checked`: matching PoB code/output/breakdown evidence has been inspected when applicable.
- `fixture_verified`: a reproducible build fixture confirms the behavior and expected value.
- `regression_locked`: the fixture is included in regression runs and changes require explicit review.

The following statuses may be attached at any state:

- `partial`: only part of the claim is proven; answer only the proven part.
- `unverified`: required evidence is missing; do not use as sole final evidence.
- `conflict`: sources or observations disagree; do not merge values or promote the rule until resolved.

`temporary_evidence` from external search is session-only and cannot advance a rule to canonical status by itself. Promotion requires separate source review and fixture verification.

## 2. Source review

Classify the claim before choosing evidence.

### Calculated value claims

Use, in order:

1. PoB output/breakdown for the exact build context
2. PoB code at the matching ref
3. Other sources as explanatory fallback

### Game-rule claims

Use, in order:

1. Official patch notes and official game data
2. PoB code at the matching ref
3. PoE Wiki and PoEDB

Record all consulted sources with license, attribution, retrievedAt, repository commit/ref, and applicable `gamePatch`, `pobVersion`, and `dataRevision`. A field that does not apply is explicitly `null` or `not_applicable`.

If sources disagree, create a `conflict` record. Do not merge wording or values merely because they appear compatible.

## 3. PoB inspection

For implementation evidence, record the standard `pobEvidence` fields:

- `repository`
- `ref`
- `file`
- `line` or `function`
- `stat`
- `modKey`
- `observedValue`
- `observationContext`

PoB inspection must distinguish an implementation fact from a universal game rule. For a calculated value, preserve the exact skill, Skill Set, Main Skill, Config, enabled state, enemy state, and raw output path used to observe it.

## 4. Fixture requirements

Every fixture used to advance a rule to `fixture_verified` must include:

```yaml
buildFile: "path/to/build.xml"
buildId: "stable fixture id"
skillSet: "Endgame"
mainSkill: "Arc of Oscillating"
config: {}
enemyState: {}
gamePatch: "3.29"
pobVersion: "<commit or release>"
expectedOutputPath: "calcs.mainEnv.player.activeSkillList[...].output"
expectedBreakdownPath: "calcs.mainEnv.player.activeSkillList[...].breakdown"
```

The version fields may be `null` or `not_applicable` only when the fixture genuinely has no applicable value. The expected output and breakdown paths must identify the PoB values used for comparison.

## 5. First-pass damage validation scope

The first pass validates:

- base/effectiveness/added damage
- gain as extra and conversion
- increased/decreased and more/less
- resistance and penetration
- hit and damage over time

The following are second-pass domains and require separate fixtures and evidence: critical strikes, ailments, projectile/chain, overlap, and DPS aggregation. Do not mark a first-pass rule as proving a second-pass behavior.

Keep `finalDamage` and `DPS` as different expected domains. A final damage fixture is not automatically a DPS fixture; DPS requires explicit rate, repetition, duration, aggregation, and overlap assumptions.

## 6. Calculation and interaction validation

Record mathematical sequence in `calculation.stages` using `stage` and `order`. Record causes separately in `dependencies`, `interactions`, and `sourceEdges`.

For each expected value, compare:

1. PoB raw internal value
2. PoB UI display value
3. Tool return value
4. Final response display value

Document presentation rounding separately from internal calculation. Preserve floating-point results, floor/ceil/round operations, and server-tick/cooldown boundaries when they affect the result.

## 7. RAG, Tool, and Evidence Graph validation

- RAG chunks are keyed by stable rule ID and contain statement, scope, conditions, source summary, version context, and uncertainty.
- Tools return facts, conditions, PoB output/breakdown, and the standard evidence envelope.
- Evidence Graph stores `sourceEdges`, calculation `stage`/`order`, source nodes, and evidence references.
- Every result envelope contains `status`, `facts`, `trace`, `sources`, `version`, `evidenceGraph`, and `uncertainty`, even when a field contains an explicit unavailable reason.
- External search is represented as `temporary_evidence` and remains session-only.

## 8. Regression locking

When a fixture reaches `regression_locked`:

- store its expected output and breakdown paths;
- rerun it against supported PoB updates;
- compare raw values before display rounding;
- review any source, patch, or PoB ref change;
- preserve the old result as historical evidence when a patch changes behavior;
- downgrade to `partial`, `unverified`, or `conflict` when the expected result can no longer be proven.

The latest version is the default target, but a version mismatch must not silently rewrite historical evidence.

## 9. Validation failure rules

- Missing user/build context: ask the user for the missing information.
- Missing rule/source/PoB evidence: do not guess; mark uncertainty and reject a definitive answer.
- Major game/PoB version mismatch: reject calculation or comparison.
- Minor version mismatch after update failure: a same-major cached result may be reused with a warning.
- Conflicting sources: preserve the conflict and do not produce one merged value.
- A failed Tool or incomplete graph: return a partial/unavailable envelope rather than inventing facts.
