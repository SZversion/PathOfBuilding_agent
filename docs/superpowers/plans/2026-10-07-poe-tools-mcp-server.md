# Local PoE Tools MCP Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose all 32 registered AgentLoop tools from a local MCP server used only by the same-PC backend.

**Architecture:** The backend launches a Python MCP server as a persistent stdio child process and calls its tools through an MCP client. The MCP server reuses existing Python knowledge/search/comparison behavior and forwards PoB operations to the running Lua process through the authenticated loopback `LivePobTransport`; it never launches the headless XML adapter for user-session tool calls.

**Tech Stack:** Python, official Python MCP SDK, existing AgentLoop/KnowledgeSearch/ExternalSearch, Lua AgentControl/AgentBridge, JSON over stdio and authenticated loopback TCP.

**Spec:** `docs/superpowers/specs/2026-10-07-poe-tools-mcp-server-design.md`

## Global Constraints

- MCP transport is local stdio; no MCP network listener and no browser.
- The MCP list must exactly equal the 32 names in `agent/orchestration/agent_loop.py:ALLOWED_TOOLS`.
- `agent/tool_catalog.py` is the single declarative record per tool: names, descriptions, schemas, required fields, and handler group. AgentLoop's allowlist and MCP definitions derive from it; add tools there once and implement the appropriate provider group. Lua-backed tools must also be added to the Lua read-only capability table, whose parity is checked by catalog lint.
- PoB memory access stays on the PoB Lua UI thread through `LivePobTransport` and the existing token-protected AgentControl socket.
- Tool results retain the established JSON result/error envelope; JSON tool payloads are returned as a single MCP text content block.
- Mutations never fall back to the headless XML adapter and return `MUTATION_NOT_PERSISTENT` until live mutation is implemented.
- Preserve all pre-existing modified and untracked files; only stage files created for this feature when committing.

## Review Focus

- PoB exits or has no active build: MCP calls return the existing structured bridge error, not a fabricated value.
- Tool arguments omit required fields, use the wrong JSON type, or include an unknown tool: MCP boundary rejects before side effects.
- A planner's snapshot revision is stale: backend rejects the operation before any mutation call.
- Mutation tools are called in live mode: return `MUTATION_NOT_PERSISTENT` and do not alter/save the build.
- MCP child crashes or writes diagnostics: backend reports a structured unavailable error; stdout remains protocol-only and no headless fallback occurs.

---

### Task 1: Canonical MCP tool contracts

**Files:**
- Create: `agent/mcp/__init__.py`
- Create: `agent/tool_catalog.py`
- Create: `agent/mcp/registry.py`
- Create: `requirements-mcp.txt`
- Test: `tests/agent/mcp/test_registry.py`

**Interfaces:**
- `tool_definitions() -> list[ToolDefinition]` returns unique canonical names, descriptions, and JSON input schemas for all 32 tools.
- `validate_tool_call(name: str, arguments: dict) -> dict` rejects unknown tools, invalid argument objects, missing required values, and wrong primitive types using existing AgentLoop argument contracts.
- `tool_definitions()` emits definitions directly from `TOOL_CATALOG`; AgentLoop's allowlist derives from the same catalog.

- [ ] **Step 1: Write failing registry tests** for exact 32-name equality, unique names, required schema/description, correct required argument fields, and invalid/unknown call rejection.
- [ ] **Step 2: Run** `pytest tests/agent/mcp/test_registry.py -q`; confirm expected failures because MCP registry is absent.
- [x] **Step 3: Implement** one catalog record per tool and derive MCP schemas and AgentLoop's allowlist from it; validate MCP calls against those schemas because planner validation intentionally rejects mutation tools.
- [x] **Step 4: Add** the MCP SDK dependency in `requirements-mcp.txt` (`mcp>=1.29,<2`; current server uses the v1 Python SDK API).
- [x] **Step 5: Run** the focused registry tests; all pass.

### Task 2: Complete the live PoB tool dispatch boundary

**Files:**
- Modify: `src/Modules/AgentControl.lua`
- Modify: `src/Modules/AgentBridge.lua`
- Modify: `src/Modules/AgentInProcess.lua` only if a small shared adapter is needed to preserve existing argument mapping
- Test: `tests/agent/tools/test_agent_bridge_dispatcher.lua`
- Test: add focused `tests/agent/tools/test_agent_control_dispatch.lua`

**Interfaces:**
- Authenticated local request remains `{op: canonicalToolName, arguments: object, token: capabilityToken}`.
- `AgentControl` forwards each of the 24 read-only PoB tools through `AgentBridge.dispatch` on the PoB UI thread.
- `compare_build_states` is dispatched to its existing Lua handler using `beforeState`, `afterState`, optional `skillIndex`, and `comparisonFields`, without loading a build file.
- Mutation names return the stable `MUTATION_NOT_PERSISTENT` error before touching build state.

- [x] **Step 1: Write failing Lua tests** covering every registered live read-only name, representative argument-mapped handlers, unknown names, and mutation rejection.
- [x] **Step 2: Run** the focused Lua tests and confirm the new routing cases failed before code changes.
- [x] **Step 3: Implement** generic dispatch through `AgentBridge.isReadOnly`, the explicit snapshot-comparison branch, and mutation capability rejection.
- [x] **Step 4: Run** focused Lua tests and all agent tool Lua self-checks; all passed.

### Task 3: Implement the local MCP tool server

**Files:**
- Create: `agent/mcp/server.py`
- Create: `agent/mcp/handlers.py`
- Test: `tests/agent/mcp/test_handlers.py`
- Test: `tests/agent/mcp/test_server_stdio.py`

**Interfaces:**
- `create_handlers(endpoint_dir=None, knowledge_search=None, external_search=None) -> dict[str, Callable]` returns exactly the 32 MCP handlers.
- PoB tools use `LivePobTransport` calls with `op` and `arguments`; startup resolves the endpoint file and token locally.
- Knowledge and alias tools use `KnowledgeSearch`; external lookup uses `ExternalSearch`; `compare_build_states` uses the existing comparison handler.
- Mutation handlers return the project's structured live capability rejection without invoking `PobBridge` headless mode.
- MCP resource `pob://current-snapshot` returns a freshly captured normalized live context and `snapshotRevision` for the backend's planner input.

- [x] **Step 1: Write failing handler tests** asserting exact name equality, correct routing to local-search/live-PoB/comparison groups, capability-gated mutations, and JSON results.
- [x] **Step 2: Run** focused handler tests; they failed before the group providers existed.
- [x] **Step 3: Implement** group-based handler construction, the 32 definitions, and `pob://current-snapshot`.
- [x] **Step 4: Write and run** stdio client tests that list all 32 tools, invoke mutation rejection, and verify protocol-only stdout.
- [x] **Step 5: Run** all MCP tests; all 15 pass without a network listener.

### Task 4: Make the backend use MCP for every tool call

**Files:**
- Create: `agent/mcp/client.py`
- Modify: `agent/cli.py`
- Modify: `agent/orchestration/runtime.py`
- Modify: `agent/orchestration/agent_loop.py` only where needed to inject MCP-discovered tool catalog and handlers
- Test: `tests/agent/mcp/test_client.py`
- Test: `tests/agent/test_cli.py`
- Test: `tests/agent/orchestration/test_runtime.py`

**Interfaces:**
- `McpToolClient.start()`, `.list_tools()`, `.call_tool(name, arguments)`, and `.close()` own one persistent stdio session for a backend run.
- Client startup verifies the MCP tool-name set equals `ALLOWED_TOOLS`; mismatch stops startup with a structured configuration error.
- `AgentLoop` receives MCP call handlers for non-knowledge tools and an MCP-backed search adapter for `search_knowledge` and both alias tools, so `execute_plan` never executes one of these locally.
- Backend captures the live snapshot through MCP/PoB transport before sending it to the LLM; the planner uses the MCP-discovered catalog and existing eight-call/revision rules.

- [x] **Step 1: Write client/server tests** for startup, catalog parity, forwarding, and process closure.
- [x] **Step 2: Run** focused MCP and CLI tests.
- [x] **Step 3: Implement** persistent stdio lifecycle, snapshot-resource reads, and MCP-backed production CLI routing; test adapters remain injectable.
- [x] **Step 4: Run** Python suite and verify representative calls over MCP stdio; live PoB smoke awaits restarting the app on the updated Lua modules.

### Task 5: Document setup and verify the integrated flow

**Files:**
- Modify: `README.md`
- Modify: `agent/README.md`
- Modify: `docs/tools/catalog.md`
- Test: `tests/agent/mcp/test_server_stdio.py` and existing AgentLoop/CLI/Lua suites

- [x] **Step 1: Document** MCP setup, the local endpoint, backend-managed stdio lifecycle, all 32 tools, and mutation behavior.
- [x] **Step 2: Run** catalog lint, MCP tests, and all agent Lua tool checks.
- [x] **Step 3: Run** the full Python suite: 113 passed, 2 skipped.
- [ ] **Step 4: Perform** the live PoB smoke test after updating/restarting PoB. Current installed AgentControl is older and its active endpoint did not return a response during this run.
- [x] **Step 5: Review** the feature changes without staging unrelated pre-existing working-tree files.

