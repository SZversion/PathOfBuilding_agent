# Local PoB Bridge

## Responsibility

The local Bridge is the only boundary between the running PoB state and the external AI server. It reads PoB's already-calculated in-process state, validates structured plans, runs allowlisted Tools, performs local RAG and approved external searches, applies requested mutations, and returns evidence.

The Bridge does not replace PoB calculations. It reads `build.calcsTab.mainEnv`, active skill output, breakdowns, modifier lists, and PoB-generated socket groups. The in-process adapter is `src/Modules/AgentInProcess.lua`; the Tool readers are in `src/Modules/AgentTool.lua` and `src/Modules/AgentMechanismTool.lua`.

## Boundary

```text
PoB UI / in-process build
        ↕
local PoB Bridge
  ├─ snapshot and revision checks
  ├─ Tool validation and execution
  ├─ local RAG and approved web search
  └─ Evidence envelope construction
        ↕ structured JSON only
external AI server
```

The external server receives normalized build data, not raw XML, and never receives a user API key. It returns a JSON plan; prose that looks like a Tool command is never executed.

## State authority

The current Skill Set, Main Skill, Config, enabled gems, buffs, charges, and enemy conditions are authoritative. A user UI change wins over an older Agent plan. Before a mutation, the Bridge compares the plan's expected revision with the current revision; on mismatch it discards the stale mutation and recaptures state.

## Query and mutation rules

Read operations expose PoB output, breakdown, source paths, and Evidence Graph nodes. Mutation operations change only the current in-memory build. They do not call Save or Save As. Existing PoB save behavior remains the user's responsibility.

## Failure behavior

Missing user context produces a clarification request. Missing PoB or knowledge evidence produces a partial/unavailable or rejected envelope rather than a guessed value. A major version mismatch rejects the operation. A same-major minor-version mismatch may use a warned cache after update failure.
