# In-process PoB Agent Bridge Design

## Status

Draft for user review. This document defines the next architectural step; it does not implement the bridge.

## Goal

Connect Agent Tools to the currently running Path of Building Lua process so that the authoritative state is the unsaved, currently visible PoB state rather than a newly loaded XML/headless copy.

The bridge must expose PoB-calculated values together with their source paths, calculation trace, Evidence Graph, and `snapshotRevision`.

## Non-goals

- Reimplementing PoE or PoB calculations.
- Changing existing PoB UI layout or removing existing behavior.
- Automatic Save or Save As.
- Build recommendation or optimization.
- Implementing the external AI server in this phase.

## Proposed architecture

```text
External AI server
        |
        | structured Tool request
        v
PoB Agent Dispatcher (inside PoB Lua process)
        |
        +-- AgentContextSnapshot
        |     +-- activeSpec
        |     +-- activeSkillSet
        |     +-- activeItemSet
        |     +-- Config / enabled state
        |     +-- snapshotRevision
        |
        +-- Read-only Tools
        |     +-- PoB output readers
        |     +-- breakdown/trace readers
        |
        +-- Mutation Tools
        |     +-- transaction backup
        |     +-- PoB mutation
        |     +-- recalculation
        |     +-- verify/commit or rollback
        |
        v
PoB calculation engine
        |
        v
Structured response envelope
```

## Request flow

1. The external model emits a canonical Tool name and JSON arguments.
2. The PoB Dispatcher validates the Tool name, arguments, snapshot revision, and mutation policy.
3. The Dispatcher captures the current in-memory context without reloading XML.
4. A read-only Tool reads PoB output/breakdown objects. A mutation Tool creates a transaction backup before changing state.
5. PoB's existing calculation pipeline is invoked.
6. The Tool builds a common response envelope containing final values, source paths, trace, Evidence Graph, conditions, and revision.
7. Mutation success commits the in-memory state only. Failure restores the backup.
8. The response is returned to the external AI server for natural-language explanation.

## Authoritative state

The current PoB process is authoritative. The snapshot must include:

- active passive tree spec;
- active skill set and main skill;
- active item set;
- current Config and enabled buffs/conditions;
- current socket groups, synthetic groups, and item-granted skills;
- game patch, PoB version, data revision;
- monotonically changing `snapshotRevision`.

The Dispatcher must capture a fresh snapshot before each Tool call. A mutation with a stale `expectedSnapshotRevision` is rejected without changing PoB state.

## Evidence and source contract

Every successful calculation response must distinguish:

- `facts`: final values read from PoB;
- `sources`: PoB object/path locations and external rule documents, if used;
- `trace`: ordered calculation or resolution steps;
- `evidenceGraph`: nodes and edges describing inputs, modifiers, and outputs;
- `conditions`: active Config and context;
- `uncertainty`: missing or non-authoritative evidence;
- `snapshotRevision`: the exact state used.

If PoB does not expose a source for a value, the Tool must return an explicit unavailable/uncertain entry rather than inventing a source.

## Mutation safety

All mutation Tools use the existing transaction contract:

1. capture current snapshot and backup;
2. validate input, revision, compatibility, and idempotency;
3. apply the mutation in memory;
4. run PoB's calculation pipeline;
5. verify expected output and trace;
6. commit with a new revision, or rollback on any failure.

No mutation Tool may call Save or Save As. If the bridge is not connected to a persistent in-process PoB session, mutation Tools must return `MUTATION_NOT_PERSISTENT` and remain disabled for live UI use.

## Error and retry behavior

- Input, alias, compatibility, stale revision, and version errors are not retried.
- Transient read-only Tool failures use the existing bounded retry policy.
- Mutation timeout or uncertain result must not immediately repeat the mutation. The Dispatcher returns `MUTATION_TIMEOUT` or `MUTATION_UNCERTAIN`, requests `REFRESH_CONTEXT`, and requires a fresh snapshot plus idempotency/revision validation before any later attempt.
- All Dispatcher failures use the common structured error envelope and the stable error registry.

## Compatibility boundary

The bridge is an additive PoB module. Existing PoB UI and calculation code remain unchanged except for a Dispatcher entry point and safe observation hooks. The first implementation may expose a local in-process API to the Agent window; network transport and external AI orchestration remain outside this phase.

## Testing plan

- Unit tests for context capture and revision changes after UI-like mutations.
- Read-only Tool tests proving values come from the current in-memory objects, not a reloaded XML.
- Source-path and Evidence Graph contract tests.
- Mutation tests for commit, rollback, stale revision, idempotency, timeout uncertainty, and no-save behavior.
- Integration fixture with active Skill Set, Config, item-granted skill, and synthetic socket group.
- Regression tests proving existing PoB calculation and Save/Save As behavior are untouched.

## Acceptance criteria

- A Tool call observes an unsaved PoB UI change without reloading XML.
- A successful mutation is visible in the current PoB state and receives a new revision.
- A failed or stale mutation leaves the PoB state unchanged.
- Every returned value includes source/trace/evidence metadata or an explicit uncertainty marker.
- Existing PoB UI and Save/Save As behavior continue to pass regression tests.
- Live mutation is never silently emulated by a one-shot headless process.
