# Bridge Capture Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Make read-only PoB Bridge snapshots deterministic and fast while preserving the active Spec, Skill Set, Item Set, calculation values, and response contract.

**Architecture:** Keep PoB's original object graph as the calculation authority. Project only the snapshot payload to primitive, sorted identifiers; never recursively serialize the calculation graph. Resolve Skill Set identity from `activeSkillSetId` first, then fixed fallbacks, without changing PoB UI state.

**Tech Stack:** Lua/LuaJIT bridge, Python orchestration tests, pytest, existing response envelope and fixture adapters.

**Spec:** `agent/AgentBridge.md`, `PRD_SDD.md`, and product planner review dated 2026-09-10.

## Global Constraints

- This branch changes read-only capture only; no external LLM, live mutation, UI, RAG, external search, or automatic save.
- `activeSpec.allocNodes` is projected into separate sorted primitive node-ID and jewel-ID arrays.
- Object/array/shared-reference/cyclic traversal is forbidden in snapshot projection; non-primitive values are dropped, never stringified.
- Skill Set resolution order is `activeSkillSetId`, active position in `skillSetOrderList`, first valid Skill Set, then the existing missing-context error contract.
- Existing response envelope, `snapshotRevision`, game/PoB/data versions, trace, sources, evidence graph, uncertainty, and registered error codes remain compatible.
- Read-only capture must not change the current PoB active state.

### Task 1: Deterministic snapshot projection

**Files:**
- Modify: `agent/pob/bridge.py`
- Modify: `src/Modules/AgentBridge.lua`
- Test: `tests/agent/orchestration/test_pob_bridge.py`
- Test: `tests/agent/tools/test_agent_bridge_dispatcher.lua`

**Interfaces:**
- Preserve the existing capture/dispatch entry points.
- Add or reuse a private projection helper that returns `allocatedNodeIds: list[int]` and `jewelIds: list[int]` in deterministic ascending order.

- [ ] Add tests for non-contiguous IDs, duplicate IDs, nil values, and a cyclic/shared-reference fixture. Assert no object graph fields are serialized.
- [ ] Add a deterministic serialization test: equivalent input order produces byte-equivalent projected snapshot payloads.
- [ ] Implement primitive projection without recursive traversal and without `str()`/string coercion of unsupported values.
- [ ] Preserve the original PoB object graph for calculations; only the outbound snapshot is projected.
- [ ] Run the focused Python and Lua tests and commit the implementation.

### Task 2: Skill Set and active-state preservation

**Files:**
- Modify: `agent/pob/bridge.py`
- Modify: `src/Modules/AgentBridge.lua`
- Test: `tests/agent/orchestration/test_pob_bridge.py`
- Test: `tests/agent/tools/test_agent_bridge_dispatcher.lua`

**Interfaces:**
- Preserve existing `activeSpec`, `activeSkillSet`, and `activeItemSet` snapshot fields.
- Preserve active IDs, actual table keys, display fallback values, and calculation context.

- [ ] Test valid `activeSkillSetId` selection even when title/label is nil.
- [ ] Test fallback order: active position, first valid set, and existing missing-context error.
- [ ] Test duplicate title/label handling uses the existing ambiguity error contract rather than title as canonical identity.
- [ ] Capture before and after state and prove read-only capture leaves active Spec/Skill Set/Item Set unchanged.
- [ ] Implement the resolver and state-preserving capture, then run focused tests and commit.

### Task 3: Regression and performance evidence

**Files:**
- Modify: `tests/agent/orchestration/test_pob_bridge.py`
- Modify: `tests/agent/tools/test_agent_bridge_dispatcher.lua`
- Create: `tests/fixtures/bridge/large_active_spec.json` if the existing fixture set has no suitable large fixture

**Interfaces:**
- Consume the capture API and projected snapshot fields from Tasks 1 and 2.
- Produce test evidence containing fixture size, elapsed capture time, payload size, and baseline comparison.

- [ ] Add a large passive-tree fixture test that asserts projected payload size is smaller than graph serialization and has no capture-time regression against the checked-in baseline.
- [ ] Assert calculated facts, breakdown, source paths, versions, revision, and common response envelope are unchanged by projection.
- [ ] Run the complete relevant Python and Lua test suites, record the exact commands and results, and commit the tests.

### Task 4: Final product review

**Files:**
- Review only; no implementation files unless a finding requires a developer fix.

**Checks:**
- Confirm every global constraint is met and no out-of-scope subsystem changed.
- Confirm QA evidence covers deterministic projection, fallback resolution, no state mutation, response compatibility, and performance.
- Any defect returns to the developer for a fix and then to the test reviewer for re-test before final approval.
