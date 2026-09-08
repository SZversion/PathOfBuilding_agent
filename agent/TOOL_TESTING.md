# Tool Testing Contract

This document defines the testing workflow for PoB Agent Tools. It references, and does not redefine, the contracts in:

- agent/TOOL_AUTHORING.md
- docs/tools/response-envelope.md
- docs/tools/catalog.md
- agent/EXCEPTION_HANDLING.md

Those files are the single sources of truth for Tool shape, response envelope, registry membership, status values, error leaf codes, and recovery classes.

## 1. Test layers

Every Implemented/Public Tool is tested through the narrowest applicable layers before integration:

1. Unit — alias normalization, input validation, path selection, delta aggregation, precision preservation, and idempotency-key handling.
2. Schema — request and response shape against the existing envelope and Tool registry; no new fields or enums are invented by tests.
3. Contract — public registry membership, required template fields, status/error separation, version and snapshot revision behavior.
4. Bridge — local Bridge dispatch, PoB output/breakdown lookup, RAG/search boundaries, snapshot capture, and exception mapping.
5. In-process — the Tool reads the authoritative PoB process state and verifies active Skill Set, Main Skill, Config, enabled state, and revision.
6. Integration — model plan → Bridge validation → Tool/RAG/search execution → envelope → model explanation.
7. Regression — stored real fixtures and prior failure cases across supported PoE1/PoB versions.

A Planned Tool may have unit-level schema and plan tests only. Planned tests must never be reported as implementation completion or public API availability.

## 2. Expected-value policy

Authoritative expected values come only from:

- PoB output and breakdown for the matching loaded state; or
- a saved, versioned PoB fixture containing the expected output and breakdown paths.

A test must not use an independently reimplemented damage, duration, projectile, resistance, or DPS formula as an authoritative expected value. Such a calculation may be a diagnostic oracle only and must be labeled non-authoritative.

Each real fixture records the build file or normalized snapshot, Skill Set, Main Skill, Config, enemy state, game patch, PoB version, expected output path, expected breakdown path, and snapshot revision. A planned/template fixture has no fabricated version or expected number.

## 3. Status and evidence assertions

Tests must distinguish the statuses defined by docs/tools/response-envelope.md:

- calculated: the requested PoB value and required evidence are available;
- partial: a usable result exists with explicit warning or incomplete evidence;
- unavailable: PoB loaded the state but the requested output is absent;
- not_simulated: the requested behavior is outside PoB's modeled calculation;
- conflict: sources disagree and are preserved separately;
- rejected: policy, version, grounding, or required-input rules prevent a safe answer.

A test passes only when status matches the evidence condition. A numerical match with missing or contradictory evidence is not a calculated-result pass.

Every evidence assertion checks version fields and same-major version policy, raw precision versus UI/final presentation rounding, uncertainty including temporaryEvidence, evidenceGraph.stages for calculation stage/order, and evidenceGraph.sourceEdges for causal provenance.

Stage/order and sourceEdges are different assertions: stage/order proves sequence; sourceEdges prove why an input contributed. A graph that puts causal edges into the stage list fails contract validation.

## 4. Category test criteria

The seven Tool categories from agent/TOOL_AUTHORING.md use these minimum criteria.

### Context · Resolution

Test Skill Set, Main Skill, Config, enemy state, enabled state, synthetic socket groups, active item-granted effects, and snapshot revision. Test English and Korean aliases against the same canonical identity. Test ambiguous aliases and missing context through the registered ASK_USER path; do not guess a skill, item, or build.

### State · Metadata

Test normalized gem identity (gemId, grantedEffectId, variantId, level, quality), item identity, passive node identity, socket/group order, version metadata, and enabled state. Verify that current values are read from the authoritative PoB snapshot and are not silently replaced by static KB values.

### Calculation

Test that the Tool reads the documented PoB output/breakdown path and returns the exact raw value plus display metadata. Test selected Skill Set/Main Skill/Config, enemy state, precision, and unavailable output paths. Any local operation must be limited to normalization, delta, or display aggregation.

### Trace · Evidence

Test ordered intermediate output references, rule IDs, PoB file/function evidence, sources, uncertainty, and Evidence Graph stage/order versus sourceEdges. Test missing, temporary, and conflicting evidence independently.

### Comparison · Simulation

Test before/after states from two PoB-calculated snapshots, delta sign and precision, changed fields, and simulation boundaries. A comparison must identify which state was authoritative and must return not_simulated where PoB does not model live behavior.

### Mutation

Test immediate in-memory application and PoB recalculation without automatic file saving. Test Save/Save As delegation, user UI precedence, revision conflict discard, full snapshot recapture, rollback on failure, idempotency, and retry prohibition after uncertain mutation results.

### Knowledge · Search

Test local RAG filtering by rule ID, patch, source, status, and uncertainty. Test approved external domains as session-only temporaryEvidence; they cannot replace PoB output or promote a rule. Test search-policy denial and missing grounding through the registered exception registry.

## 5. Alias, identity, and ambiguity tests

For every public Tool accepting a name, create cases for exact English name, exact Korean alias including whitespace, variant/alternate/awakened/greater identity, item-granted skill versus socketed skill, allowed case or punctuation normalization, an ambiguous alias, and an unknown alias.

English and Korean inputs must resolve to the same canonical PoB identity when the alias table proves that relationship. Ambiguous or missing identity returns the registered ASK_USER path (AMBIGUOUS_ALIAS or USER_CONTEXT_MISSING), not a best-effort guess.

## 6. Exception and recovery tests

Use only leaf codes in agent/EXCEPTION_HANDLING.md. For each failure case, assert the exact registered error.code, its single primary error.recovery_class, that secondary_causes do not override the primary class, that retryable behavior follows the registry, and that an unknown code normalizes to UNCLASSIFIED_FAILURE and FATAL_INTERNAL.

Test at least missing JSON, invalid input, Tool not found, timeout, stale revision, grounding missing/conflict, version mismatch/warning, search policy denial, PoB calculation error, and mutation failure using existing registry entries.

## 7. Budgets and retries

For every user request assert tool_call_count <= 8, counting Tool, RAG, approved-search, and all retries. The LLM retry counter is independent and follows agent/EXCEPTION_HANDLING.md. A Tool retry receives no separate unbounded allowance.

Mutation retries require both a valid idempotency key and revalidated current snapshot revision. A timeout or uncertain mutation result must first recapture and reconcile; it must not immediately repeat the mutation.

## 8. Mutation safety

Mutation tests must verify that screen/in-memory state changes are visible immediately, no file is saved automatically, PoB Save and Save As remain the user's action, a user UI change after the Agent snapshot wins, revision mismatch discards the Agent mutation and recaptures a full snapshot, rollback restores previous state on failure, repeating an idempotency key cannot duplicate a change, and a stale diff is never merged into newer user state.

## 9. Parallel development and baseline revisions

Before integration tests, record the tested repository revision, PoB reference, fixture revision, and knowledge-data revision. If parallel development changes a shared bridge, Tool registry, response envelope, or fixture while a test is running, stop the affected run, record conflicting revisions and files, do not mark partial evidence passed, reconcile through the project owner or review agent, and rerun from a clean recorded baseline.

## 10. Fixture matrix

Representative real fixtures should cover Arc of Oscillating variant identity/tags/level/quality/chain/cast speed; Static Strike of Gathering Lightning, Trauma, duration, and support compatibility; Impending Doom/Vixen's Entrapment item-granted skill, synthetic socket group, support order, and curse interaction; variant, awakened, greater, alternate-quality, and corrupted gems; passive and ascendancy allocation before/after with source trace; attribute changes and actor/skill stat source traces; weapon hand swap with local/global modifiers; unique item override/granted-skill interaction; armour defence change; ring/amulet/belt comparison; quest reward act/class/patch reference; and build comparison from PoB code.

A missing real fixture keeps the related rule or Tool behavior planned/unverified. A planned/template fixture may validate input shape only.

## 11. Completion report and review agent procedure

A development completion report must contain Tool name/category, registry state in docs/tools/catalog.md, implementation and test baseline revisions, test layers and pass/fail counts, fixture IDs and PoB output/breakdown paths, observed statuses and raw expected values, Evidence Graph and source-edge coverage, alias/ambiguity results, mutation/revision/idempotency results, Tool and LLM retry counts, and known gaps, uncertainty, temporary evidence, and planned fixtures.

The review agent checks TOOL_AUTHORING, response-envelope, catalog membership, exception mapping, authoritative expected values, Planned Tool status, diff/schema/regression results, and returns approval, requested changes, or rejection with evidence.

Only after review approval and required real fixtures reach fixture_verified may a Tool behavior be called complete or canonical.

