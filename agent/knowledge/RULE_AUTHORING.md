# Rule Authoring Guide

This guide defines how to write canonical Path of Exile 1 rules for the PoB Agent knowledge base. Canonical rules are written in English. Korean names and aliases remain separate retrieval data.

## 1. Scope and version metadata

The knowledge base targets the latest supported Path of Exile 1 version, but version metadata is contextual rather than universally mandatory. Every rule, source, evidence record, and verification record should include `gamePatch`, `pobVersion`, and `dataRevision` when those values apply. If a value does not apply or is unavailable, use `null` or `not_applicable`; do not invent a version.

Recommended metadata:

```yaml
gamePatch: "3.29"
pobVersion: "<commit or release>"
dataRevision: "<source-data revision>"
```

Use `null` for an unknown value and `not_applicable` for a source or fact that is not version-scoped. A patch-sensitive rule must not be generalized across versions without a verification record.

## 2. Rule record structure

Each rule should contain:

- stable `id`, category, English statement, and terms
- facts and formulas in machine-readable form
- scope: `global`, `actor`, `skill`, `support`, `item`, `passive`, `enemy`, `hit`, `ailment`, `dot`, `projectile`, or `config`
- applicable version metadata
- source metadata and source priority
- PoB evidence when the rule concerns implementation or calculated output
- verification state and verification notes
- uncertainty/conflict information when evidence is incomplete

Write one rule for one claim. Do not combine a general game rule, a particular PoB implementation detail, and a build-specific result into one record.

## 3. Source priority by rule type

Source priority is not global; it depends on what is being claimed.

### Calculated values

1. PoB output or breakdown for the exact build context
2. PoB code at the matching version/ref
3. Other sources, only as explanatory or fallback evidence

### Game rules

1. Official patch notes and official game data
2. PoB code at the matching version/ref
3. PoE Wiki and PoEDB

PoB output is authoritative for the current build's calculated value, not automatically for a universal game-rule statement. A Wiki or PoEDB statement is explanatory evidence, not a replacement for a current PoB output.

If sources disagree, do not silently merge, average, or select the convenient value. Record `verification: conflict`, preserve each source, explain the scope/version difference, and block canonical promotion until reviewed.

## 4. PoB evidence authoring

When a rule is supported by PoB implementation or a current calculation, preserve a `pobEvidence` object with these standard fields:

```yaml
pobEvidence:
  repository: "PathOfBuildingCommunity/PathOfBuilding"
  ref: "<commit, tag, or branch>"
  file: "src/Modules/CalcOffence.lua"
  line: "1878-1945"
  function: null
  stat: "TotalDPS"
  modKey: null
  observedValue: "<value or behavior>"
  observationContext: "<build, skill, config, and patch context>"
```

When multiple files or observations support one rule, use an array of the same objects. Do not combine file paths or line ranges in one string.

Use `line` or `function` as appropriate; one of them must identify the implementation location. `stat` and `modKey` may be `null` when not applicable. Keep the observed value separate from an interpretation.

Source metadata must preserve `license`, `attribution`, `retrievedAt`, and repository `commit` whenever available. This applies to official data, PoB source, wiki extracts, PoEDB data, and Craft of Exile material.

## 5. Calculation stages versus causes

Do not use one list to represent two different relations.

### Calculation order

`stage`/`order` records the mathematical sequence, such as:

```text
base/effectiveness → added/gain/conversion → increased/decreased
→ more/less → resistance/penetration → hit or DoT result → aggregation
```

The exact order must be stated only when the relevant PoB output/breakdown or fixture proves it.

### Causal relations

`dependencies`, `interactions`, and `sourceEdges` record why a stage has an input. For example, a support gem can contribute to a skill's projectile count and also gate a separate damage stage. A passive can affect both the actor and a skill through different scopes.

Evidence Graph consumers use `sourceEdges` for these causal links; they must not infer mathematical order from edge order.

## 6. Precision authoring rules

Record and transport these precision layers separately:

- internal PoB calculation precision: preserve the raw numeric value
- UI display precision: the value shown by PoB
- Tool return precision: preserve raw value plus a display value/unit
- final response rounding: presentation only, never a new calculation

Document whether a result is affected by floating-point behavior, discrete floor/ceil/round operations, server ticks, cooldown ticks, or other simulation boundaries. A value that is continuous in PoB must not be presented as a server-tick guarantee. Keep `rawValue`, `displayValue`, `rounding`, and `tickRule` distinct where relevant.

## 7. First and second rule scopes

The first damage-rule authoring pass covers:

- base, effectivity/effectiveness, and added damage
- gain as extra and conversion
- increased/decreased and more/less
- resistance and penetration
- hit and damage over time

The second pass separately covers critical strikes, ailments, projectile/chain behavior, overlap, and DPS aggregation. A rule from the first pass must not claim to cover these second-pass domains.

Keep `finalDamage` and `DPS` as separate domains. `finalDamage` describes one resolved damage event or damage instance; `DPS` includes rate, repetition, duration, hit frequency, or aggregation assumptions.

## 8. RAG and Tool authoring

RAG documents are chunked by stable `rule-id`; each chunk should contain the statement, conditions, scope, source summary, and uncertainty. RAG explains rules and interactions; it does not replace a current PoB value.

Tools return `facts`, conditions, and PoB output/breakdown. Evidence Graph records `sourceEdges`, calculation `stage`/`order`, and evidence references. Keep these representations linked by stable IDs rather than duplicating prose.

External search results are `temporary_evidence` only. They can inform the current answer, but canonical rule promotion requires separate source review and fixture verification.

## 9. Authoring checklist

- Is the claim one rule and written in English?
- Is the scope explicit?
- Are applicable version fields present, or explicitly `null`/`not_applicable`?
- Is source priority appropriate for the claim type?
- Are conflicts preserved rather than merged?
- Is PoB evidence recorded with the standard fields when applicable?
- Are calculation order and causal edges separate?
- Is precision and tick behavior explicit?
- Is uncertainty stated?
- Is the rule in the correct first- or second-pass domain?
