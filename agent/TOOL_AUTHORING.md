# Tool Authoring Contract

This document defines how PoB Agent Tools are designed, registered, reviewed, and promoted. It is subordinate to the product and architecture documents and uses the English canonical terms in those documents.

## Authoritative references

- `docs/tools/catalog.md` is the authoritative Tool registry. Only entries under **Implemented and public** may be called by the model in production. Entries under **Planned Tools** are design requirements, not callable APIs.
- `docs/tools/response-envelope.md` is the single authoritative response-format specification. This document does not redefine the envelope, status enum, or evidence graph shape.
- `agent/EXCEPTION_HANDLING.md` is the authoritative error-code and `recovery_class` registry. Tool authors must not invent error codes.
- `RULE_SCHEMA.md` and `VALIDATION_WORKFLOW.md` define rule evidence, version fields, precision, and promotion gates.

The response `status` describes the successful or usable result state (`calculated`, `partial`, `unavailable`, `not_simulated`, `conflict`, or `rejected`). An exception is represented separately by the registered `error.code` and `error.recovery_class` contract in `agent/EXCEPTION_HANDLING.md`. A successful result with `status: partial` and `VERSION_WARNING` is not an exception; an execution failure with `status: error` must carry a registry error and recovery class.

## Tool categories

Every Tool belongs to one primary category:

1. **Context · Resolution** — select Skill Set, Main Skill, Config, aliases, synthetic groups, and authoritative snapshot context.
2. **State · Metadata** — expose normalized build, gem, item, passive, version, and snapshot metadata.
3. **Calculation** — read PoB output/breakdown and return values with provenance.
4. **Trace · Evidence** — expose intermediate output paths, modifier sources, ordered stages, and Evidence Graph edges.
5. **Comparison · Simulation** — compare two PoB-calculated states or explain a delta; simulation boundaries must be explicit.
6. **Mutation** — apply an approved in-memory item/gem/passive change and recalculate.
7. **Knowledge · Search** — query local RAG or approved external sources.
8. **Internal common layer** — snapshot/revision checks, alias normalization, version policy, envelope construction, budget accounting, and error mapping. This layer is not a public user Tool.

## Required Tool template

Every Tool specification and implementation must document all fields below. A missing field keeps the Tool `planned`.

```yaml
name: get_skill_dps
category: Calculation
registry: docs/tools/catalog.md
status: implemented/public | planned
inputSchema:
  type: object
  properties:
    skillIndex: {type: integer, minimum: 1}
  required: [skillIndex]
aliasNormalization:
  accepts: [skill display name, English alias, Korean alias, numeric index]
  canonical: activeSkillList index plus resolved gem identity
pobPath:
  output: activeSkillList[skillIndex].output.TotalDPS
  breakdown: activeSkillList[skillIndex].breakdown
facts: PoB output values and resolved metadata
conditions: Skill Set, Main Skill, Config, enemy state, and enabled state
trace: ordered PoB stages and intermediate output references
sources: PoB paths, rule IDs, fixture IDs, and temporary evidence when applicable
evidenceGraph: nodes, stages, and sourceEdges using docs/tools/response-envelope.md
version: gamePatch, pobVersion, dataRevision
snapshotRevision: captured revision and authoritative-state hash
sideEffect: none
idempotency: read-only; safe to repeat for the same snapshot revision
retry:
  codes: use only agent/EXCEPTION_HANDLING.md
  recovery: registered recovery class and bounded action
fixture:
  references: []
  promotionState: planned | source_checked | pob_checked | fixture_verified | canonical
```

The concrete response uses the common envelope from `docs/tools/response-envelope.md`; the template above describes its required contents and does not create an alternative envelope.

## Calculation boundary

Calculation Tools must read the authoritative PoB `output` and `breakdown` produced by the loaded build. They must not reimplement PoB damage, duration, projectile, resistance, or DPS formulas. Local code is limited to:

- input and alias normalization;
- selecting the correct Skill Set/Main Skill/Config and output path;
- delta and before/after aggregation for comparisons;
- display grouping and presentation rounding, never calculation rounding;
- attaching trace, source, version, snapshot, and Evidence Graph metadata.

If the PoB output or breakdown does not contain the requested value, return the common envelope with `status: unavailable` or `status: not_simulated`; do not substitute an independently calculated value. A `temporary_evidence` search result may explain a missing game rule but cannot replace a PoB-calculated value.

## Context and version rules

The PoB in-process state is authoritative for the current request: active Skill Set, Main Skill, Config, enabled gems, active buffs, enemy state, and current revision. A Tool captures these before execution and records the revision in its result. Major game/PoB mismatch is rejected. Same-major minor/patch mismatch may continue with the registered `VERSION_WARNING` and explicit uncertainty.

All numeric results preserve PoB raw precision. UI and final-answer rounding is presentation-only. Tick behavior is recorded separately; a PoB tick model does not prove live server timing.

## Mutation rules

Mutation Tools are the only Tools allowed to change build state.

- Apply changes to the current in-memory PoB state immediately and recalculate through PoB.
- Never save automatically. File persistence remains under the existing PoB Save/Save As actions.
- User UI changes have precedence over Agent changes.
- Every mutation carries the captured snapshot revision and an idempotency key.
- If the revision changed before commit, discard the mutation, return the registered `SNAPSHOT_REVISION_CONFLICT`/`REFRESH_CONTEXT` path, and recapture a full snapshot.
- Do not retry a mutation after timeout or an uncertain result unless idempotency and the current revision have been revalidated.
- A stale or untrusted diff is discarded; it is never merged into the newer user state.

Mutation results must include before/after facts, delta, changed fields, recalculated PoB outputs, and source edges. The result must make clear that the screen changed but no file was saved.

## Search and RAG rules

The local Bridge executes local RAG and approved external search. External search is session-scoped `temporary_evidence`; it is not automatically canonical and cannot override PoB output. Approved sources and source metadata must be preserved. A rule cannot be promoted to canonical or authoritative without `fixture_verified`, even if a Wiki page appears clear.

RAG chunks are one claim per `rule-id` and carry patch applicability, source metadata, status, uncertainty, and relevant PoB evidence. Planned, unverified, and conflict records may be retrieved to explain uncertainty but must be excluded from authoritative final-value retrieval.

## Tool budget and recovery

For one user request, `tool_call_count <= 8`, including Tool retries, RAG calls, and approved-search calls. This counter is independent of the LLM retry counter. LLM repair attempts follow `agent/EXCEPTION_HANDLING.md` and do not consume Tool calls unless they cause a Tool invocation.

Tool authors must use the existing exception registry. Do not create new error codes in Tool code or documentation. Map failures to the registered code and recovery class, preserve the attempt and snapshot context, and stop at the bounded retry ceiling.

## Promotion and fixture policy

`planned/template` fixtures describe an intended scenario and contain no fabricated version or output. Real fixtures identify the build file or normalized snapshot, Skill Set, Main Skill, Config, enemy state, game patch, PoB version, expected output path, and expected breakdown path.

Promotion requires the validation state appropriate to the claim, and `fixture_verified` is mandatory before a rule, Tool behavior, or output path is called canonical/authoritative. A missing fixture yields `planned` or `unverified`; a source disagreement yields `conflict` and is never merged.

## Review checklist

- Is the Tool registered in `docs/tools/catalog.md` with the correct public/planned state?
- Does the implementation read the correct PoB output/breakdown path rather than reimplementing the formula?
- Are input aliases normalized to a canonical PoB identity?
- Are Skill Set/Main Skill/Config, version, snapshot revision, conditions, and enabled state recorded?
- Are facts, trace, sources, and Evidence Graph present in the common response envelope?
- Are side effects, idempotency, retry/recovery codes, and mutation revision rules explicit?
- Is every external source marked temporary until reviewed and fixture-verified?
- Does the fixture status prevent premature canonical promotion?

