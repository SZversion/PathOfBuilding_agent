# POB Agent Chat Window Design

## Goal

Add an in-application, chat-style Agent window to Path of Building while keeping the existing PoB visual language and build workflow intact.

## User-approved direction

- Place an Agent button in the upper toolbar, in the blank space immediately to the right of `Save As` and before the center divider, as marked in the user's screenshot.
- Clicking the button expands a chat window inside PoB.
- This implementation covers the screen UI only; connecting messages to the Agent service is out of scope.

## Design

Add a compact Agent button in the upper toolbar's blank space immediately to the right of `Save As` and before the center divider, matching the location marked in the user's screenshot. The button toggles a small overlay chat panel within the current PoB window. The panel opens near the upper-left corner of the main build content area, over the passive tree area shown in the user's screenshot, with a compact default size of about 240 by 180 UI units. The user can resize it by dragging its lower-right corner; keep its bounds within the current build viewport and enforce a compact minimum size. The panel uses PoB's existing dark surfaces, borders, typography, and text color conventions, and does not replace the active build tab.

The chat panel contains a title/header with a close control, a scrollable conversation area with a short welcome or example assistant message, a multiline message input, and a send control. Since there is no backend connection in this scope, the UI must not imply that an Agent answered or that a build change was applied. Local presentation state may show the typed user message, but no generated response is displayed.

The panel is opened and closed from the adjacent button and close control. Its initial position is the upper-left of the main build content area; its dimensions can be adjusted with the lower-right resize handle. Existing build state, save behavior, tabs, and calculations remain unchanged. The UI should fit the existing PoB viewport and retain normal access to the rest of the app when the panel is closed.

## Implementation boundary

- Add the entry button and overlay behavior to the existing build screen.
- Reuse PoB control and drawing conventions where practical.
- Keep UI state local to the current build screen session.
- Do not add HTTP calls, Agent orchestration, credentials, persistence, or build mutations.
- Do not change existing PoB save or tab behavior.

## Acceptance criteria

1. The Agent button appears in the marked upper-toolbar space to the right of `Save As` and before the center divider.
2. Clicking the button opens a compact chat panel in the upper-left of the main build content area; clicking the button again or the close control closes it.
3. The panel presents a conversation area, message input, and send affordance in PoB's visual style.
4. The panel can be resized from its lower-right corner and stays within the build viewport, with a compact minimum size.
5. No network request or simulated Agent response occurs.
6. Opening, closing, and resizing the panel does not change build data or interfere with the selected build tab.
7. The panel remains usable at the supported PoB viewport sizes, including the existing compact-header layout.

## Self-review

- Scope is limited to one in-app UI addition and does not introduce a new service boundary.
- The top-bar controls are laid out in `src/Modules/Build.lua`; the button must stay within the marked gap between `Save As` and the center divider at supported window widths.
- The panel starts in the upper-left of the main build content area at about 240 by 180 UI units and clamps resizing to the build viewport.
- No unresolved placeholders or contradictory requirements remain.
