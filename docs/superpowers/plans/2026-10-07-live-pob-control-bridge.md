# Live PoB Control Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Let the local PoB Agent list and open an exact saved build in the running PoB process, then read its PoB-calculated DPS without screenshots or keyboard shortcuts.

**Architecture:** Add a loopback-only newline JSON endpoint to the PoB Lua process. Poll it non-blockingly from `main:OnFrame`, validate requests against a small allowlist, and execute PoB actions on the UI thread. Connect the Python live bridge to this endpoint through a per-session capability file in the current user's PoB data directory.

**Tech Stack:** PoB Lua 5.1/LuaSocket, existing `AgentInProcess` and `AgentTool` modules, Python standard library socket/JSON.

**Spec:** `docs/superpowers/specs/2026-10-07-live-pob-control-bridge-design.md`

## Global Constraints

- Bind the transport to IPv4 loopback only.
- Accept only bounded JSON requests from the allowlisted command catalog.
- Run all PoB state reads and mutations on the PoB UI thread.
- Never evaluate caller-provided Lua or accept arbitrary build file paths.
- Preserve unsaved state; do not auto-save or suppress PoB prompts.
- Read DPS only from PoB's existing calculated output and preserve evidence/conditions.

## Review Focus

- Malformed or oversized frames do not stall the PoB frame loop — protocol tests.
- Unauthorized or stale build IDs cannot open a different file — handler tests.
- Unsaved current builds are preserved when a load is requested — load handler tests.
- A client timeout or disconnect does not leave a client socket or block rendering — transport tests.
- A missing module or unsupported runtime fails closed without disabling PoB — startup smoke check.

---

### Task 1: PoB-side local command service

**Files:**
- Create: `src/Modules/AgentControl.lua`
- Modify: `src/Modules/Main.lua`
- Test: `spec/System/TestAgentControl_spec.lua`

**Interfaces:**
- Produces `AgentControl:Init(main)` and `AgentControl:OnFrame()`; only `Main.lua` owns and polls the service.
- Accepts `list_builds`, `load_build`, `capture_snapshot`, `get_skill_dps`, and `get_highest_dps_skill`.

- [ ] Write tests for request allowlisting, build listing/loading, unsaved-state rejection, and read-only Tool results.
- [ ] Run the new tests and confirm each fails for the missing service behavior.
- [ ] Implement a bounded non-blocking JSON-line loopback server, per-session capability metadata, and main-thread command dispatch.
- [ ] Hook initialization and polling into `main:Init` / `main.onFrameFuncs` with safe shutdown and fail-closed startup.
- [ ] Run focused Lua tests and syntax validation.

### Task 2: Python live transport client

**Files:**
- Create: `agent/pob/live_transport.py`
- Modify: `agent/pob/live_bridge.py` only if required by the new transport boundary.
- Test: `tests/agent/pob/test_live_transport.py`

**Interfaces:**
- Produces `LivePobTransport.request(payload) -> dict` and discovers the current session from the per-user endpoint metadata file.
- Consumes the JSON-line protocol produced by Task 1.

- [ ] Write tests for connect/read deadlines, token validation, malformed responses, and absent endpoint metadata.
- [ ] Run the new tests and confirm the expected failures.
- [ ] Implement bounded socket framing and structured protocol errors without logging the token.
- [ ] Run focused Python tests and type/syntax checks.

### Task 3: Install and exercise the local bridge

**Files:**
- Modify: `packaging/` installer scripts as needed.
- Modify: `docs/architecture/bridge.md` and `agent/AgentBridge.md`.
- Test: PoB live smoke workflow.

**Interfaces:**
- Installs only the additive Agent Lua modules and records the endpoint metadata under the current user's PoB data directory.
- Exposes build-list and exact-load operations to the local Agent process.

- [ ] Add a reversible install/uninstall path that leaves stock PoB files and user builds intact.
- [ ] Document restart requirements, unsaved-build protection, protocol operations, and failure recovery.
- [ ] Run the real PoB workflow: list build names, load the exact Arc build, capture the live snapshot, and read a matching DPS field.
- [ ] Record any PoB-version or runtime limitations; do not claim live control until the smoke workflow succeeds.
