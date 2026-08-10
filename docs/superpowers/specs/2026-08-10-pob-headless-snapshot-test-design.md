# PoB Headless Snapshot Test Design

## Goal

Run the existing PoB calculation pipeline against one user-provided PoB XML build and verify that the AgentSnapshot bridge receives the recalculated in-memory result and can expose one calculation explanation.

## In scope

- Use the repository's existing `src/HeadlessWrapper.lua` entry point.
- Install or obtain LuaJIT only if it is missing from the test environment.
- Load one read-only user build fixture: `Imported build.xml`.
- Execute PoB's existing `LoadDB` and `CalcsTab:BuildOutput()` flow.
- Verify `build.agentSnapshot` is created after calculation.
- Verify `build.explainAgentStat("Life")` returns a value and trace envelope.
- Keep the test fixture outside the repository unless a future user-approved fixture policy is added.

## Out of scope

- Changes to PoB calculation formulas.
- New Agent Tool APIs or model integration.
- UI changes.
- RAG or prompt changes.
- Bulk processing of all user builds.
- Persisting user builds or snapshots into the repository.
- Replacing PoB's XML parser or calculation pipeline.

## Design

The test runner will execute the existing HeadlessWrapper in the repository root. The test script will read the user XML path, call `loadBuildFromXML`, allow the normal frame/calculation flow to complete, and assert the snapshot and explanation contracts. The AgentSnapshot implementation remains the only bridge under test; PoB source modules are not modified for this stage.

## Verification

1. Confirm LuaJIT is available; install it only when absent.
2. Run the focused user-build test.
3. Run the existing lightweight snapshot self-check if the runtime supports it.
4. Validate that no source files outside the snapshot bridge and test runner changed.

## Failure handling

- Missing LuaJIT: install a local test runtime or report the environment blocker.
- Invalid XML: fail with the exact fixture path and parser error.
- Missing snapshot/explanation: fail at the first missing contract.
- Do not modify or overwrite the user's build file.
