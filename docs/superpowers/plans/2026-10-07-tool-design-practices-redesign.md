# PoE MCP Tool Design Practices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the 32 public MCP tool contracts with the course tool-design topics and the repository's authoring, error, and result standards.

**Architecture:** Keep public tool names and local stdio transport. Enrich the canonical catalog, derive MCP descriptions/schemas/annotations and docs from it, and normalize results/errors at the MCP boundary. Preserve AgentLoop's sequential composition, live PoB transport, and mutation gate.

**Tech Stack:** Python, MCP Python SDK, existing AgentLoop/runtime, Lua PoB dispatch, pytest, LuaJIT.

**Spec:** `docs/superpowers/specs/2026-10-07-tool-design-practices-redesign.md`

## Global Constraints

- Keep all 32 names; do not add a browser or network-facing MCP listener.
- PoB state remains live and UI-thread authoritative through authenticated Lua dispatch.
- Only registered errors and recovery classes may cross the tool boundary.
- Read-only idempotent calls may retry only for registered transient codes within the eight-call budget.
- Mutations always return `MUTATION_NOT_PERSISTENT` before adapter dispatch.

## Review Focus

- A field omitted or given a wrong type fails before a provider call.
- A handler exception or timeout returns one canonical error envelope and is not reported as successful.
- Transient read errors retry only when the spec permits; mutations never retry.
- MCP annotations agree with actual tool side effects.
- The docs-render check detects stale generated sections and Lua/catalog drift.

---

### Task 1: Complete canonical per-tool contracts

**Files:**
- Modify: `agent/tool_catalog.py`
- Modify: `agent/mcp/registry.py`
- Test: `tests/agent/mcp/test_registry.py`

**Interfaces:**
- `ToolSpec` contains category, provider group, model-facing description fields, input schema, result description, side-effect/retry/timeout policy, error codes, examples, and MCP annotations.
- `tool_definitions()` renders all 32 stable names from `TOOL_CATALOG`.

- [x] Add failing tests for complete fields, category/group distinction, field descriptions, stable names, metadata consistency, and invalid-input rejection.
- [x] Run the focused test and confirm it fails on the missing metadata.
- [x] Enrich all 32 records and derive JSON schemas and MCP annotations from those records.
- [x] Run registry and planner schema tests.

### Task 2: Normalize handler outcomes and retry behavior

**Files:**
- Modify: `agent/mcp/handlers.py`
- Modify: `agent/mcp/client.py`
- Modify: `agent/orchestration/runtime.py`
- Modify: `agent/EXCEPTION_HANDLING.md` only if a required leaf code is not registered
- Test: `tests/agent/mcp/test_handlers.py`
- Test: `tests/agent/mcp/test_client.py`
- Test: `tests/agent/orchestration/test_runtime.py`

**Interfaces:**
- MCP success is a common envelope preserving PoB evidence and placing local/search results in `facts`.
- MCP failures carry registered `error_ref`, `error_code`, recovery class, attempt bounds, and safe details; client raises a typed `ToolCallError` only for `isError` responses.
- Runtime maps `ToolCallError` into the step contract and retries only explicitly retryable, idempotent read-only calls.

- [x] Add failing tests for local/search/PoB normalization, registered errors, timeout classification, retry eligibility, and mutation no-retry behavior.
- [x] Run focused tests and verify expected failures.
- [x] Implement shared result/error normalization and bounded retry forwarding.
- [x] Run handler, client, and runtime tests.

### Task 3: Publish descriptions, composition guidance, and generated docs

**Files:**
- Modify: `agent/mcp/server.py`
- Modify: `agent/orchestration/agent_loop.py`
- Modify: `agent/TOOL_AUTHORING.md`
- Modify: `docs/tools/catalog.md`
- Modify: `tools/lint_agent_catalog.py`
- Create: `tools/render_mcp_tool_catalog.py`
- Test: `tests/agent/mcp/test_server_stdio.py`
- Test: `tests/agent/mcp/test_catalog_docs.py`

**Interfaces:**
- MCP Tool descriptions include purpose, use conditions, constraints, and results; property schemas carry per-field descriptions.
- Server returns the catalog's read-only/destructive/idempotent/open-world annotations and proper MCP `isError` flags.
- Generated docs are deterministic; PoB path/evidence and fixture status remain manually curated.
- Planner sees the discovered read-only catalog and preserves sequential, revision-aware, eight-call composition.

- [x] Add failing tests for generated metadata/docs parity, annotations, MCP error flags, planner discovery, and multi-step policy.
- [x] Run focused stdio/planner tests and verify expected failures.
- [x] Implement catalog rendering and amend authoring rules to distinguish executable contract from evidence documentation.
- [x] Run focused tests and catalog lint.

### Task 4: Integrated verification and setup guidance

**Files:**
- Modify: `README.md`
- Modify: `agent/README.md`
- Modify: `docs/superpowers/specs/2026-10-07-tool-design-practices-redesign.md`
- Test: all MCP, CLI, AgentLoop, runtime, and Lua tool checks

- [x] Run catalog/docs lint and all focused suites.
- [x] Run the full Python suite and all Lua agent tool checks.
- [x] Exercise stdio list/call/error flows; report live PoB smoke separately if the currently installed Lua module has not been restarted.
- [x] Review the final diff without staging unrelated dirty files; no commit or staging performed.
