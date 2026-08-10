# Internal PoB Tool Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a small read-only Lua tool module that normalizes PoB's calculated in-memory values and breakdowns into the approved Fact Envelope.

**Architecture:** `AgentTool.lua` will validate inputs, read `build.calcsTab.mainEnv`, and delegate explanations to `AgentSnapshot.explain`. It will not recalculate values or alter PoB modules. Tests will use fake calculation tables plus the existing external-build smoke runner.

**Tech Stack:** LuaJIT, existing PoB Lua modules, `assert`-based tests.

## Global Constraints

- No Qwen/API model, UI, HTTP/MCP server, natural-language routing, RAG, or prompt changes.
- No PoB calculation formula changes.
- Tool functions are read-only.
- Every tool returns `envelope` or `nil, error`.
- `trace` is an empty table for non-explanation tools.
- `get_projectile_count` reads `activeSkillList[skillIndex].output.ProjectileCount`.
- `get_curse_limit` reads `player.output.EnemyCurseLimit`.

---

### Task 1: Add the internal tool module

**Files:**
- Create: `src/Modules/AgentTool.lua`

**Interfaces:**
- Consumes: `build.calcsTab.mainEnv`, `AgentSnapshot.explain`.
- Produces: `get_character_stats`, `get_skill_stats`, `get_projectile_count`, `get_curse_limit`, `explain_stat`.

- [ ] **Step 1: Implement shared validation and envelope helpers**

Use a single helper that returns:

```lua
{ calculationVersion = "...", facts = { }, sources = { "..." }, trace = { } }
```

Return `nil, "..."` for missing build state, non-integer/out-of-range skill indexes, or absent requested values.

- [ ] **Step 2: Implement the five read-only functions**

Map facts exactly as approved:

```lua
get_character_stats(build) -> facts = scalar player output
get_skill_stats(build, index) -> facts = { skillIndex, name, skillPart, trigger, output }
get_projectile_count(build, index) -> facts = { skillIndex, value = skill.output.ProjectileCount }
get_curse_limit(build) -> facts = { value = player.output.EnemyCurseLimit }
explain_stat(build, stat, index) -> facts = { stat, value }, trace = AgentSnapshot.explain(...).trace
```

- [ ] **Step 3: Keep the module independent of UI**

Do not modify `CalcsTab.lua` unless a binding is required by the existing runtime; direct callers pass the current `build` object.

- [ ] **Step 4: Commit the module**

```powershell
git add src/Modules/AgentTool.lua
git commit -m "feat: add internal PoB calculation tools"
```

### Task 2: Add focused contract tests

**Files:**
- Create: `tests/agent/tools/test_agent_tool.lua`

**Interfaces:**
- Consumes: `AgentTool.lua` and fake `build.calcsTab.mainEnv` tables.
- Produces: deterministic pass/fail checks for envelope shape and errors.

- [ ] **Step 1: Test valid character, skill, projectile, curse, and explanation results**

Assert `calculationVersion`, `facts`, `sources`, and `trace` for each function. Use a fake skill with `ProjectileCount = 3` and player `EnemyCurseLimit = 2`.

- [ ] **Step 2: Test invalid input behavior**

Assert `nil, error` for missing build state, index `0`, fractional index, out-of-range index, missing stat, and missing projectile/curse output.

- [ ] **Step 3: Run the focused test**

```powershell
& 'C:\Users\SZ\AppData\Local\Programs\LuaJIT\bin\luajit.exe' tests/agent/tools/test_agent_tool.lua
```

Expected: the test prints a pass message and exits with code 0.

- [ ] **Step 4: Commit the tests**

```powershell
git add tests/agent/tools/test_agent_tool.lua
git commit -m "test: verify internal PoB tool contracts"
```

### Task 3: Run the external user-build smoke test

**Files:**
- Modify only if needed: `tests/agent/tools/test_user_build_headless.lua`

**Interfaces:**
- Consumes: the approved external XML build and the internal Tool module.
- Produces: smoke-test evidence that real PoB output keys feed the tools.

- [ ] **Step 1: Add tool loading to the test runner**

Load `Modules/AgentTool` after `HeadlessWrapper.lua` initializes and call `get_projectile_count(build, build.mainSocketGroup)` and `get_curse_limit(build)`.

- [ ] **Step 2: Assert real values are present**

Assert both calls return envelopes with non-nil `facts.value`, without hard-coding patch-sensitive numbers.

- [ ] **Step 3: Run the smoke test**

```powershell
$env:POB_AGENT_TEST_BUILD = 'C:\Users\SZ\Documents\Path of Building\Builds\3.29\Imported build.xml'
Set-Location src
& 'C:\Users\SZ\AppData\Local\Programs\LuaJIT\bin\luajit.exe' '../tests/agent/tools/test_user_build_headless.lua'
```

Expected: snapshot, projectile, curse, and Life explanation checks pass.

- [ ] **Step 4: Commit the smoke-test update**

```powershell
git add tests/agent/tools/test_user_build_headless.lua
git commit -m "test: exercise PoB tools with external build"
```

### Task 4: Final scope verification

**Files:**
- No new files.

- [ ] **Step 1: Check changed paths**

```powershell
git status --short
git diff HEAD~3 --name-only
```

Expected: only `src/Modules/AgentTool.lua`, `tests/agent/tools/`, and plan documents changed.

- [ ] **Step 2: Run both focused tests**

```powershell
& 'C:\Users\SZ\AppData\Local\Programs\LuaJIT\bin\luajit.exe' tests/agent/tools/test_agent_tool.lua
& 'C:\Users\SZ\AppData\Local\Programs\LuaJIT\bin\luajit.exe' tests/agent/tools/test_agent_snapshot.lua
```

Expected: both pass; the external smoke test remains the authoritative PoB integration check.
