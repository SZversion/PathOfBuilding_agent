# AgentBridge Specification

## 1. Purpose

`AgentBridge` is the in-process boundary between the running Path of Building (PoB) Lua application and the Agent Tool layer. It makes PoB's current in-memory state authoritative so Tools can read unsaved UI changes and, when live mutation mode is enabled, apply validated changes to the current PoB state without saving files.

This document defines the bridge contract and implementation boundary. It does not define the external AI server or natural-language prompting.

## 2. Goals

- Read the currently active PoB state without reloading XML.
- Preserve active passive tree spec, Skill Set, Item Set, Config, enabled effects, synthetic socket groups, and item-granted skills.
- Dispatch canonical Tool requests to PoB-native Tool handlers.
- Return PoB values with source paths, trace, Evidence Graph, conditions, uncertainty, and `snapshotRevision`.
- Apply mutations transactionally when a persistent in-process session is available.
- Preserve existing PoB UI, calculation, Save, and Save As behavior.

## 3. Non-goals

- Reimplementing PoB or PoE calculations.
- Automatically saving or creating build files.
- Recommending an optimal build or searching every possible combination.
- Owning model inference, RAG, external search, or user-facing conversation UI.
- Silently treating a one-shot headless XML process as a live PoB session.

## 4. Runtime modes

### 4.1 Live in-process mode (planned)

The target architecture runs the Dispatcher inside the active PoB Lua process and holds references to the current build, tabs, calculation environment, and revision state. The current implementation does not yet provide live mutation dispatch; until that work is complete, live in-process use is read-only.

### 4.2 Headless adapter mode

The existing one-shot Lua/XML bridge can be used for fixtures and read-only development tests. Mutation Tools are disabled by default in this mode and return:

```json
{
  "code": "MUTATION_NOT_PERSISTENT",
  "recovery_class": "REJECT",
  "stage": "bridge_capability",
  "next_action": "reject_request",
  "retryable": false,
  "attempt": 1,
  "max_attempts": 1,
  "details": {},
  "side_effect": "none",
  "operator_message": "Live mutation is disabled until an in-process PoB session is connected",
  "snapshotRevision": null
}
```

The adapter must never claim that a mutation was applied to the user's current PoB window.

## 5. Components

### 5.1 `AgentBridge`

Owns lifecycle and capability state. It exposes `live` or `headless` mode, current build identity, and whether mutation is enabled.

### 5.2 `AgentContextSnapshot`

Captures a fresh authoritative context before every request:

- active passive tree spec;
- active Skill Set and main skill;
- active Item Set;
- Config, enabled buffs, enemy and calculation conditions;
- socket groups, support links, synthetic groups, and item-granted skills;
- game patch, PoB version, and data revision;
- monotonic `snapshotRevision`.

Snapshots are observations, not independent build authorities. A new snapshot is required after UI changes, recalculation, rollback, or uncertain execution.

### 5.3 `AgentDispatcher`

Validates the canonical Tool name and JSON arguments, checks capabilities and revision, invokes the Tool handler, and wraps success or failure in the common response envelope. In the current implementation, the in-process dispatcher supports context capture and read-only dispatch; explicit mutation and comparison dispatch with revision/idempotency checks are planned work.

### 5.4 `AgentMutation`

Provides backup, validation, mutation, PoB recalculation, verification, commit, rollback, and idempotency handling. It never calls Save or Save As.

### 5.5 `AgentTrace`

Collects PoB object paths and calculation evidence. It must distinguish values directly read from PoB output from values supported only by external rule knowledge.

## 6. Request contract

```json
{
  "tool": "get_skill_dps",
  "arguments": {
    "skillIndex": 1
  },
  "expectedSnapshotRevision": "rev-42",
  "idempotencyKey": "required-for-mutations",
  "fingerprint": "required-for-mutations"
}
```

Rules:

- Tool names must be present in the public catalog and Dispatcher registry.
- Arguments are validated before PoB state is touched.
- A stale `expectedSnapshotRevision` rejects mutations without side effects.
- Read-only requests may capture a fresh revision when no revision was supplied.
- Mutation requests require an idempotency key, fingerprint, and current revision.

## 7. Success response contract

Every successful response contains:

- `status` and `version`;
- `facts` with final values;
- `conditions` describing the active PoB context;
- `trace` with ordered operations;
- `sources` with PoB object paths or rule documents;
- `evidenceGraph` with nodes and typed edges;
- `uncertainty` when evidence is missing or non-authoritative;
- `snapshotRevision` used for the result;
- `side_effect`, `saved`, and `operator_message`.

For mutations, the response also contains before/after facts, delta, changed fields, and the new committed revision.

## 8. Source and trace rules

Source entries must identify the actual PoB object or output field, for example:

```text
PoB:CalcsTab.mainEnv.player.activeSkillList[1].output.ProjectileCount
PoB:SkillsTab.activeSkillList[1].activeEffect.grantedEffect
PoB:ItemsTab.activeItemSet[Helmet]
```

The bridge must not invent a source path. When PoB does not expose a direct source, it must return an explicit unavailable or uncertain marker and may attach an external rule source separately.

## 9. Mutation protocol

1. Capture current context and backup in-memory state.
2. Validate arguments, capability, compatibility, revision, and idempotency.
3. Apply the requested item, gem, passive, or other supported mutation.
4. Invoke PoB's existing recalculation pipeline.
5. Verify output, source trace, and expected state transition.
6. Commit in memory and increment `snapshotRevision`.
7. On any failure, restore the backup and return a structured error.

Mutation timeout or uncertain result must not immediately repeat the mutation. Return `MUTATION_TIMEOUT` or `MUTATION_UNCERTAIN`, request `REFRESH_CONTEXT`, and require a fresh snapshot plus revision/idempotency validation before any later attempt.

## 10. Error contract

All bridge errors use the stable registry in `agent/EXCEPTION_HANDLING.md` and include:

- `code`;
- `recovery_class`;
- `stage`;
- `next_action`;
- `retryable`;
- `attempt` and `max_attempts`;
- `message` and structured `details`;
- `snapshotRevision` when available;
- `side_effect`.

Important bridge errors:

- `MUTATION_NOT_PERSISTENT`: live PoB session is unavailable;
- `SNAPSHOT_REVISION_CONFLICT`: requested mutation is stale;
- `MUTATION_TIMEOUT`: mutation result is unknown;
- `MUTATION_UNCERTAIN`: verification could not establish the result;
- `VALUE_UNAVAILABLE`: PoB did not expose the requested value or source.

## 11. User-change precedence

The latest user/UI state always wins over an older Agent plan. Any detected revision change invalidates pending mutation plans. The bridge must recapture the current state rather than replaying an old plan.

## 12. Testing requirements

- Capture an unsaved UI-like change and prove the next read-only Tool sees it without XML reload.
- Verify active Spec, Skill Set, Item Set, Config, synthetic groups, and item-granted skills.
- Verify source paths, trace ordering, Evidence Graph edges, and uncertainty markers.
- Test planned mutation dispatch commit, rollback, stale revision, idempotency, timeout, and no-save behavior once live mutation dispatch is implemented.
- Test headless mode rejection of mutation Tools.
- Run regression tests for existing PoB calculations and Save/Save As behavior.

## 13. Acceptance criteria

- Current in-process read-only mode reads the current PoB memory state.
- Planned live mutation mode will make a successful mutation visible in the current PoB window and return a new revision.
- A stale, failed, timed-out, or uncertain mutation does not silently alter the build.
- Every returned value is traceable to PoB output or explicitly marked uncertain.
- Existing PoB behavior remains intact.
- Headless mode never presents fixture mutation as live UI mutation.
