# Live PoB Control Bridge Design

## Goal

Let the local PoB Agent enumerate saved builds, open one selected build in the running Path of Building process, and read the resulting PoB-calculated values without screen capture or keyboard shortcuts.

## Current state

- `AgentInProcess.lua` can access the active PoB build and dispatch read-only Tools, but it is not loaded by the installed PoB copy.
- `LivePobBridge` accepts an injected transport; no transport to the running Lua VM is currently implemented.
- The installed PoB `Modules` directory has no `Agent*.lua` files.
- PoB's own build list uses `BuildListControl:LoadBuild` and `main:SetMode` to open builds.
- Existing Computer Use screenshot capture is unreliable in this environment and is not part of this design.

## Proposed design

Add a small local command endpoint to the PoB Lua process and service it from `main:OnFrame`, so all PoB operations run on the UI thread. The endpoint accepts bounded JSON requests, validates a per-process capability token, queues each request, and returns a structured JSON response. Bind only to IPv4 loopback; do not expose a general Lua evaluator, arbitrary path access, or remote network listener.

This is preferred over Windows accessibility because PoB's custom controls are absent from its accessibility tree and frame capture currently times out. The existing one-shot XML bridge is not suitable for controlling the open window or observing unsaved state. A loopback transport reuses LuaSocket already present in PoB; the token must be generated with an OS-backed random source and stored in per-user local application data with inherited user-only access. Loopback binding alone is not treated as authentication.

The initial command catalog is deliberately narrow:

1. `list_builds`: return stable build IDs and display names from PoB's existing build list.
2. `load_build`: accept only a stable ID returned by `list_builds`; ask PoB's existing mode transition to open that build. If the current build has unsaved changes or a save prompt is active, return a structured `USER_ACTION_REQUIRED` result and do not discard state.
3. `capture_snapshot`: return the current active build context through `AgentInProcess`.
4. `get_skill_dps` and `get_highest_dps_skill`: return existing PoB Tool output, including its conditions and source/evidence fields.

The Python `LivePobBridge` will use the local endpoint as its request transport. The protocol will reject unknown operations, malformed JSON, oversized messages, stale build IDs, invalid tokens, and unsupported PoB versions with the existing structured error envelope.

## Scope

### In scope

- A same-user, loopback-only IPC transport between the local Agent process and PoB's Lua process.
- Main-thread dispatch for build listing, exact build loading, snapshot capture, and DPS reads.
- Safe handling of unsaved state and stale build selections.
- Startup and shutdown lifecycle for the endpoint.
- Documentation for enabling the module in the PoB installation.

### Out of scope

- Arbitrary Lua execution or arbitrary filesystem paths in requests.
- General build edits such as replacing items, gems, or passives.
- Automatic saving, Save As, or suppressing PoB's existing prompts.
- Remote network access, UI redesign, keyboard automation, or screen-capture changes.

## Acceptance criteria

- The local Agent can list the running PoB instance's saved build names without reading the screen.
- Loading requires an unambiguous stable ID from that list and uses PoB's normal build-loading path.
- An unsaved current build is preserved; the endpoint reports that user action is required instead of dropping it.
- After a successful load, snapshot and DPS commands read the active in-memory PoB build, including unsaved in-memory context.
- Requests are limited to the current user on loopback and to the allowlisted command catalog.
- The feature is disabled cleanly when the module, transport, token, or PoB version is unavailable.

## Risks and constraints

- The currently running PoB installation does not include the Agent Lua modules. Enabling this design for that process will require installing the additive module and restarting PoB; this design does not authorize losing or overwriting an unsaved build.
- PoB's custom-drawn controls are not exposed through Windows accessibility, so IPC must call supported PoB methods rather than synthesize clicks.
- LuaSocket is available in the repository runtime, but OS-backed token generation, token-file ACLs, request framing, and the non-blocking lifecycle must be validated against the packaged PoB Lua runtime before use.
- If PoB is busy calculating, requests must remain queued or return a bounded timeout; the endpoint must never block the render/input loop on a client.

## Verification evidence required

- Protocol tests for allowlisted operations, token checks, malformed/oversized requests, stale IDs, and timeout behavior.
- Lua-level tests for listing, loading, unsaved-state protection, and read-only Tool dispatch.
- A real PoB smoke run showing `list_builds` → exact `load_build` → `capture_snapshot` → `get_skill_dps` without screenshots or keyboard shortcuts.
