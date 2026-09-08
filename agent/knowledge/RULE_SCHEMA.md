# Canonical Rule and Evidence Schema

This document describes the logical schema for English canonical PoE1 rules. Existing JSON files may adopt fields incrementally; this document is the target contract for new or promoted records. Version fields are contextual and allow `null` or `not_applicable` when they do not apply.

## 1. Rule envelope

```yaml
id: "damage.projectile.base"
category: "damage"
statement: "A projectile skill starts with its configured base projectile count."
terms: ["projectile", "base count"]
scope: "projectile"
domain: "finalDamage"
facts: {}
conditions: []
gamePatch: "3.29"
pobVersion: null
dataRevision: "not_applicable"
sources: []
pobEvidence: null
calculation: {}
dependencies: []
interactions: []
sourceEdges: []
verification: {}
uncertainty: {}
```

Required semantic fields are `id`, `category`, `statement`, `scope`, `domain`, `sources`, and `verification`. `gamePatch`, `pobVersion`, and `dataRevision` are required when applicable and otherwise must be explicit `null` or `not_applicable`.

Allowed `scope` values are:

`global`, `actor`, `skill`, `support`, `item`, `passive`, `enemy`, `hit`, `ailment`, `dot`, `projectile`, `config`.

Allowed calculation domains begin with `finalDamage` and `DPS`. They must not be conflated.

## 2. Source metadata

```yaml
- id: "source-1"
  type: "pob|official|wiki|poedb|craft_of_exile|test|temporary_evidence"
  title: "..."
  url: "..."
  repository: "PathOfBuildingCommunity/PathOfBuilding"
  ref: "<commit or tag>"
  commit: "<repository commit when available>"
  license: "..."
  attribution: "..."
  retrievedAt: "2026-09-08T00:00:00Z"
  gamePatch: "3.29"
  pobVersion: null
  dataRevision: null
```

`temporary_evidence` is never canonical by itself. Its promotion requires source review, version assessment, and fixture verification.

## 3. PoB evidence

When the claim comes from PoB code or calculated output, use this exact logical object:

```yaml
pobEvidence:
  repository: "PathOfBuildingCommunity/PathOfBuilding"
  ref: "<commit or release>"
  file: "src/Modules/CalcOffence.lua"
  line: "3466-3475"
  function: null
  stat: "ElementalPenetration"
  modKey: null
  observedValue: "<raw observed output or behavior>"
  observationContext: "<build id, skill, config, enemy, patch>"
```

`line` or `function` identifies the location. `stat` and `modKey` identify the relevant output/modifier key when applicable. The observation context must be sufficient to distinguish a universal implementation observation from a build-specific result.

## 4. Calculation structure

`calculation` contains order, precision, and operation nodes, while causal relations live outside it.

```yaml
calculation:
  stages:
    - id: "base"
      stage: 1
      order: ["base", "effectiveness", "added"]
      operation: "SUM_BASE"
      inputs: []
      output: "damage.base"
    - id: "more"
      stage: 2
      order: ["increased", "more"]
      operation: "PRODUCT_MORE"
      inputs: []
      output: "damage.modified"
  precision:
    internal: "PoB raw numeric"
    ui: "PoB display precision"
    tool: "raw value plus unit"
    final: "presentation rounding only"
    floatingPoint: "preserve raw result"
    serverTick: "not_applicable"
```

`stage`/`order` means calculation sequence. It is not a source relationship.

## 5. Causal relation structure

```yaml
dependencies:
  - from: "support.greater-chain"
    to: "projectile.chain.max"
    condition: "support enabled and linked"
interactions:
  - id: "item-skill-link"
    participants: ["item.vixens", "skill.curse-a"]
    effect: "changes application order"
sourceEdges:
  - from: "item.mod.1"
    to: "calculation.stage.more"
    relation: "contributes_to"
    evidence: ["source-1"]
```

These relations explain why an input exists. They do not establish the mathematical order; that belongs to `calculation.stages`.

## 6. Evidence/uncertainty envelope

Every promoted Tool or answer evidence envelope uses:

```yaml
status: "calculated|partial|unavailable|conflict|rejected"
facts: {}
conditions: []
trace: []
sources: []
version:
  gamePatch: "3.29"
  pobVersion: null
  dataRevision: null
evidenceGraph:
  nodes: []
  sourceEdges: []
  stages: []
uncertainty:
  level: "none|low|medium|high"
  reasons: []
  missingEvidence: []
  temporaryEvidence: false
```

The version fields may be `null` or `not_applicable` where appropriate. A `conflict` status preserves competing evidence and must not be rendered as a single authoritative value. A `rejected` result explains why no answer was produced.

## 7. Precision fields

Numeric facts should use:

```yaml
value:
  raw: 10.296000000000001
  unit: "seconds"
  uiDisplay: "10.296"
  toolDisplay: "10.296000000000001"
  finalDisplay: "10.296"
  rounding: "presentation_only"
  floatingPoint: "preserve_raw"
  tickRule: "not_applicable"
```

Discrete game behavior must record floor/ceil/round and server tick behavior separately. Never use final display rounding as a calculation input.

## 8. Damage and DPS domain split

`finalDamage` facts describe a resolved hit or DoT damage instance. `DPS` facts describe damage over time or repeated events and must include rate, repetition, duration, aggregation, or overlap conditions. Critical, ailment, projectile/chain, overlap, and DPS aggregation rules are second-pass domains even when a first-pass damage rule feeds them.
