<!-- Status: Historical
Authority: Not authoritative
Superseded by: AGENT.md, PRD_SDD.md, CUSTOMER.md, agent/knowledge/RULE_AUTHORING.md, agent/knowledge/RULE_SCHEMA.md, agent/knowledge/VALIDATION_WORKFLOW.md -->
# PoB Headless Snapshot Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute the existing PoB calculation pipeline against the user's `Imported build.xml` and verify the AgentSnapshot and explanation contracts.

**Architecture:** Keep the PoB source and AgentSnapshot bridge unchanged. Add one test-only Lua runner that reads an external XML path from `POB_AGENT_TEST_BUILD`, invokes `HeadlessWrapper.lua` from the `src` working directory, loads the XML through `loadBuildFromXML`, and asserts the recalculated in-memory snapshot. The user file remains outside the repository and is never overwritten.

**Tech Stack:** PoB Lua runtime, LuaJIT, PowerShell environment variable, existing Lua `assert` checks.

## Global Constraints

- Use the repository's existing `src/HeadlessWrapper.lua` entry point.
- Use the existing PoB `LoadDB` and `CalcsTab:BuildOutput()` flow.
- Do not modify PoB calculation formulas, UI, Agent Tool APIs, model integration, RAG, or prompts.
- Read `C:/Users/SZ/Documents/Path of Building/Builds/3.29/Imported build.xml` only; never write to it.
- Keep the test fixture outside the repository.
- Approval documents requested by the user are HTML; this implementation plan remains Markdown because the planning skill requires Markdown.

---

### Task 1: Provision and verify LuaJIT

**Files:**
- No repository files.

**Interfaces:**
- Produces a callable `luajit` executable on `PATH` for the focused test.

- [ ] **Step 1: Check for an existing runtime**

Run from the repository's `src` directory:

```powershell
Get-Command luajit -ErrorAction SilentlyContinue
Get-Command winget -ErrorAction SilentlyContinue
```

Expected: If `luajit` exists, record its path and skip installation. Otherwise continue.

- [ ] **Step 2: Install LuaJIT only when missing**

Run:

```powershell
winget search LuaJIT
```

Install the exact available LuaJIT package returned by the search, then open a new shell and verify:

```powershell
luajit -v
```

Expected: LuaJIT prints its version and exits successfully.

- [ ] **Step 3: Record the runtime result**

Run:

```powershell
luajit -e "print(_VERSION)"
```

Expected: A successful Lua version line; do not commit machine-specific install paths.

### Task 2: Add the focused external-build runner

**Files:**
- Create: `tests/agent/tools/test_user_build_headless.lua`

**Interfaces:**
- Consumes: `POB_AGENT_TEST_BUILD` absolute XML path.
- Produces: process exit failure on an unmet snapshot contract; success output containing snapshot skill count and Life value.

- [ ] **Step 1: Write the test runner**

Create (the runner is invoked from `src`, so it prepends the repository Lua module paths):

```lua
local buildPath = assert(os.getenv("POB_AGENT_TEST_BUILD"), "POB_AGENT_TEST_BUILD is required")
package.path = "../runtime/lua/?.lua;../runtime/lua/?/init.lua;" .. package.path
package.cpath = "../runtime/?.dll;" .. package.cpath
local file = assert(io.open(buildPath, "r"))
local xml = file:read("*a")
file:close()

dofile("src/HeadlessWrapper.lua")
loadBuildFromXML(xml, "Agent external build test")
runCallback("OnFrame")

assert(build.agentSnapshot, "agent snapshot was not created")
assert(build.agentSnapshot.outputs, "snapshot outputs are missing")
assert(#build.agentSnapshot.skills > 0, "snapshot skills are missing")

local explanation = assert(build.explainAgentStat("Life"))
assert(explanation.value ~= nil, "Life explanation has no value")
print("user build snapshot test passed: skills=" .. #build.agentSnapshot.skills .. ", life=" .. tostring(explanation.value))
```

- [ ] **Step 2: Validate the runner has no repository fixture dependency**

Run:

```powershell
rg -n "POB_AGENT_TEST_BUILD|Documents/Path of Building|Documents\\Path of Building" tests/agent/tools/test_user_build_headless.lua
```

Expected: Only `POB_AGENT_TEST_BUILD` appears; the test must not hard-code the user's path.

- [ ] **Step 3: Commit the focused runner**

Run:

```powershell
git add tests/agent/tools/test_user_build_headless.lua
git commit -m "test: add external PoB build headless runner"
```

### Task 3: Run the user-build calculation and verify the bridge

**Files:**
- Test only: `tests/agent/tools/test_user_build_headless.lua`

**Interfaces:**
- Consumes: LuaJIT from Task 1 and the external XML path.
- Produces: passing headless calculation test or a concrete PoB/Lua runtime error.

- [ ] **Step 1: Set the read-only fixture path**

Run:

```powershell
$env:POB_AGENT_TEST_BUILD = 'C:\Users\SZ\Documents\Path of Building\Builds\3.29\Imported build.xml'
```

- [ ] **Step 2: Execute the focused test from the repository root**

Run:

```powershell
luajit ../tests/agent/tools/test_user_build_headless.lua
```

Expected: `user build snapshot test passed: ...` and exit code 0.

- [ ] **Step 3: Verify the input file was not changed**

Run:

```powershell
Get-FileHash -LiteralPath $env:POB_AGENT_TEST_BUILD -Algorithm SHA256
git status --short
```

Expected: The build file remains readable and no unrelated repository files are modified.

- [ ] **Step 4: Commit only test-scope changes**

Run:

```powershell
git status --short
```

Expected: Clean worktree after the runner commit; do not commit user build data or generated snapshots.

