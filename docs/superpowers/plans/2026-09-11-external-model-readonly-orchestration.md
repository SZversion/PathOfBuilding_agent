# External Model Read Only Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Connect an external LLM to the local PoB Bridge for read-only natural-language questions, structured Tool plans, authoritative PoB results, Evidence Graph context, and Korean final answers.

**Architecture:** The external model receives a normalized full snapshot on the first request and validated diffs thereafter. It returns a structured plan only. The local runtime validates the plan against a read-only catalog, checks revision and call budgets, executes Tools through the Bridge, and sends only the common response envelope back to the model.

**Tech Stack:** Python orchestration/runtime, JSON Schema, existing provider abstraction, existing PoB Bridge and Tool envelopes, pytest.

**Spec:** `PRD_SDD.md`, `AGENT.md`, `CUSTOMER.md`, and `agent/AgentBridge.md`.

## Global Constraints

- This branch is read-only orchestration only. No live mutation, automatic save, UI change, model download, or search implementation expansion.
- Mutation Tools (`replace_item`, `replace_gem`, `change_passive`) are rejected before Bridge execution. Read-only comparison and explanation Tools remain allowed.
- The external endpoint must be explicitly configured. No localhost or local Qwen fallback is allowed.
- The model receives normalized snapshot/diff, never raw XML, local paths, API keys, or credentials.
- Tool calls per user request are limited to 8 total, including retries. Transient Tool retries are limited to 3 attempts per Tool call.
- Exact duplicate calls (same Tool and canonical arguments) are rejected; the same Tool with different arguments is allowed.
- Every failure uses the existing structured error envelope with `code`, `recovery_class`, `stage`, `attempt`, `max_attempts`, and `next_action`.

### Task 1: Read-only plan schema and catalog validation

**Files:**
- Modify: `agent/orchestration/planner.py`
- Modify: `agent/orchestration/agent_loop.py`
- Modify: `agent/tools/README.md` or catalog documentation if needed
- Test: `tests/agent/orchestration/test_planner.py`

**Requirements:**
- Define explicit schema for `intent`, `steps`, `tool`, `arguments`, `expectedSnapshotRevision`, and optional plan metadata.
- Define a separate read-only allowlist and reject mutation Tools before execution.
- Validate per-Tool required argument types and revision format.
- Reject unknown Tools, free-text commands, unsupported extra fields according to the schema policy, and mutation arguments.
- Allow the same Tool with different canonical arguments; reject exact duplicate calls.

### Task 2: External provider and error contract

**Files:**
- Modify: `agent/providers/openai_compatible.py`
- Modify: `agent/orchestration/agent_loop.py`
- Test: `tests/agent/orchestration/test_runtime.py`
- Test: `tests/agent/orchestration/test_agent_loop.py`

**Requirements:**
- Require an explicit non-local endpoint and model configuration.
- Do not include API keys or credentials in prompts, snapshots, logs, or returned facts.
- Map model parse/schema errors to `RETRY_LLM`; transient provider errors to bounded retry; revision conflicts to `REFRESH_CONTEXT`; grounding failures to `REJECT`.
- Separate LLM retry count from the total Tool-call budget.
- Preserve the common response/error envelope for all failures.

### Task 3: Snapshot/diff orchestration and Tool result handoff

**Files:**
- Modify: `agent/orchestration/runtime.py`
- Modify: `agent/orchestration/agent_loop.py`
- Modify: `agent/pob/bridge.py` only if a read-only adapter boundary is missing
- Test: `tests/agent/orchestration/test_runtime.py`
- Test: `tests/agent/orchestration/test_agent_loop.py`

**Requirements:**
- First request sends normalized full snapshot; subsequent requests send validated diff.
- Record the snapshot revision used to create the model plan.
- Check the current revision immediately before every Tool execution and reject stale plans without side effects.
- If diff generation is uncertain, send a full snapshot instead.
- Send the model only the common Tool envelope: facts, conditions, trace, sources, Evidence Graph, version, revision, uncertainty, and minimal structured errors.
- Do not treat a result without authoritative evidence as a confirmed number.

### Task 4: End-to-end read-only tests and QA evidence

**Files:**
- Test: `tests/agent/orchestration/test_agent_loop.py`
- Test: `tests/agent/orchestration/test_runtime.py`
- Test: `tests/agent/orchestration/test_pob_bridge.py` if needed for integration coverage
- Create: `tests/fixtures/orchestration/read_only_plan.json` if a fixture is needed

**Requirements:**
- Cover malformed JSON, unknown Tool, invalid arguments, exact duplicate calls, stale revision, Tool timeout, 8-call overflow, provider failure, mutation rejection, and missing Evidence Graph.
- Run a real PoB fixture read-only scenario and verify the returned facts and Evidence Graph are preserved.
- Record exact test commands and distinguish environment-blocked tests from implementation failures.

### Task 5: Final review

Review the full branch against this plan and the product documents. Confirm no mutation, UI, RAG expansion, external search expansion, or local model fallback was added. Resolve all critical/important findings before declaring completion.
