# POB Agent Chat Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PoB-styled chat panel that opens from an Agent button in the marked upper toolbar space, without connecting it to the Agent service.

**Architecture:** Add a focused `AgentChatPane` overlay class that owns chat presentation, local message state, input controls, and resize state. Integrate it with the build screen's existing overlay list, initialize it near the upper-left of the main build content at about 240 by 180 UI units, and place a toggle button immediately right of `Save As` and left of the center divider.

**Tech Stack:** Path of Building Community Lua UI (`newClass`, `ControlHost`, `Control`, `EditControl`, custom overlay drawing).

**Spec:** `docs/superpowers/specs/2026-10-07-pob-agent-chat-window-design.md`

## Global Constraints

- Keep the PoB visual language and existing build workflow intact.
- Place the Agent button in the upper toolbar, in the blank space immediately to the right of `Save As` and before the center divider.
- Clicking the button expands a chat window inside PoB.
- The chat panel opens near the upper-left corner of the main build content area, over the passive tree area shown in the user's screenshot, with a compact default size of about 240 by 180 UI units.
- The user can resize the panel by dragging its lower-right corner; keep its bounds within the current build viewport and enforce a compact minimum size.
- This implementation covers the screen UI only; connecting messages to the Agent service is out of scope.
- Do not add HTTP calls, Agent orchestration, credentials, persistence, or build mutations.
- Do not change existing PoB save or tab behavior.
- Do not add or run tests for this screen-only change.

## Review Focus

- Compact window widths can cause the `Save As` button and Agent button to collide with the center divider; keep the Agent button inside the available left toolbar gap.
- Small viewports can make the initial panel or resize handle extend beyond the content area; clamp position and dimensions and enforce the minimum size.
- Opening, closing, and resizing the overlay must preserve the selected build tab and build state.
- Clicks inside the panel must not activate controls behind it, and clicks outside must keep the existing overlay behavior.
- Keyboard input must remain directed to the chat input while it is focused and return to the build screen after close.
- Sending a message may append only a local user message; it must not display a generated response or perform a network request.

---

### Task 1: Build the chat overlay component

**Files:**
- Create: `src/Classes/AgentChatPane.lua`

**Interfaces:**
- Consumes: PoB's `newClass`, `ControlHost`, `Control`, `EditControl`, and existing drawing/input APIs.
- Produces: `AgentChatPaneClass` with `ToggleOverlay()`, `IsMouseInOverlay(cursorX, cursorY)`, `HandleOverlayClick(key, cursorX, cursorY)`, `HandleOverlayRelease(key)`, and `DrawOverlay(viewPort, inputEvents)` methods compatible with `buildMode.overlayPanes`.

- [ ] **Step 1: Define the pane and its local state**

Create `AgentChatPane` as a `ControlHost` and `Control` class. Keep visibility, local user messages, and input focus in the pane instance; do not persist them.

- [ ] **Step 2: Add the chat controls and drawing**

Render the pane initially at the upper-left of the main build content area with a compact default size of about 240 by 180 UI units. Include a PoB-style header with a close affordance, a conversation area with a clearly labeled welcome/example assistant message, a multiline edit control, a send control, and a lower-right resize handle. The send action may append the input as a user message and clear the input; it must never fabricate an Agent reply.

- [ ] **Step 3: Implement overlay bounds and event handling**

Keep the panel within `viewPort`, clamp its minimum dimensions to 200 by 150 UI units and its maximum dimensions to the available viewport, and route clicks inside it to its controls. Consume panel clicks to prevent click-through, support resizing from the lower-right handle, and close it from the header control. Delegate keyboard and character events to the pane's selected edit control while the pane is open; release focus cleanly when it closes.

- [ ] **Step 4: Commit the component**

```bash
git add src/Classes/AgentChatPane.lua
git commit -m "feat: add POB agent chat overlay"
```

### Task 2: Integrate the toolbar button with the build screen

**Files:**
- Modify: `src/Modules/Build.lua`

**Interfaces:**
- Consumes: `AgentChatPaneClass` methods from Task 1.
- Produces: an Agent toolbar button and a pane registered with `buildMode.overlayPanes`.

- [ ] **Step 1: Create the pane with build-screen state**

Initialize one `AgentChatPane` for the build screen and add it to `self.overlayPanes`, following the existing overlay lifecycle. Ensure a newly opened build starts with the pane closed.

- [ ] **Step 2: Add the toolbar toggle button**

Add an `Agent` button immediately to the right of `self.controls.saveAs` in the upper-left toolbar. Derive its position/availability from the existing center divider (`anchorTopBarRight`) so it stays within the marked gap at supported window sizes.

- [ ] **Step 3: Route overlay input and drawing**

Use the existing overlay input loop and draw-after-tab loop to route events to `AgentChatPane` and render it above the active tab. Keep normal build controls and tab selection unchanged while the panel is closed.

- [ ] **Step 4: Review the final diff**

Inspect `Build.lua` integration and the new pane against every acceptance criterion in the spec. Confirm by code inspection that no service call, persistence, or build mutation was added.

- [ ] **Step 5: Commit the integration**

```bash
git add src/Modules/Build.lua
git commit -m "feat: add POB agent chat toolbar entry"
```

## Self-Review

- Spec coverage: button location and toggle are in Task 2; PoB-style chat contents, local-only input, and overlay behavior are in Task 1; no network, persistence, or build mutation is constrained in both tasks.
- Step scan: each implementation step targets a single component or integration action; commits are scoped to their task files.
- Interface consistency: the pane methods in Task 1 match the methods Task 2 consumes and the existing `overlayPanes` lifecycle.
- Review focus: compact layout, viewport clamping, build-state preservation, click-through, focus routing, and no fake response/network activity are explicitly called out for review.
- Proportion: two tasks cover the single UI component and its build-screen integration without restructuring unrelated controls.
