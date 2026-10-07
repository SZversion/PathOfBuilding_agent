# POB Agent Chat Window Design

## Goal

Add an in-application, chat-style Agent window to Path of Building while keeping the existing PoB visual language and build workflow intact.

## User-approved direction

- Place an Agent button beside the `Current build: …` control in the upper-left area of the build screen.
- Clicking the button expands a chat window inside PoB.
- This implementation covers the screen UI only; connecting messages to the Agent service is out of scope.

## Design

Add a compact Agent button adjacent to the existing current-build control in `src/Modules/Build.lua`. The button toggles an overlay chat panel rendered within the current PoB window. The panel uses PoB's existing dark surfaces, borders, typography, and text color conventions, and does not replace the active build tab.

The chat panel contains a title/header with a close control, a scrollable conversation area with a short welcome or example assistant message, a multiline message input, and a send control. Since there is no backend connection in this scope, the UI must not imply that an Agent answered or that a build change was applied. Local presentation state may show the typed user message, but no generated response is displayed.

The panel is opened and closed from the adjacent button and close control. Existing build state, save behavior, tabs, and calculations remain unchanged. The UI should fit the existing PoB viewport and retain normal access to the rest of the app when the panel is closed.

## Implementation boundary

- Add the entry button and overlay behavior to the existing build screen.
- Reuse PoB control and drawing conventions where practical.
- Keep UI state local to the current build screen session.
- Do not add HTTP calls, Agent orchestration, credentials, persistence, or build mutations.
- Do not change existing PoB save or tab behavior.

## Acceptance criteria

1. The Agent button appears beside `Current build: …` in the upper-left build header.
2. Clicking the button opens the chat panel within the PoB window; clicking the button again or the close control closes it.
3. The panel presents a conversation area, message input, and send affordance in PoB's visual style.
4. No network request or simulated Agent response occurs.
5. Opening and closing the panel does not change build data or interfere with the selected build tab.
6. The panel remains usable at the supported PoB viewport sizes, including the existing compact-header layout.

## Self-review

- Scope is limited to one in-app UI addition and does not introduce a new service boundary.
- The current-build control is identified in `src/Modules/Build.lua` and adapts position for smaller screens; placement must account for that responsive behavior.
- No unresolved placeholders or contradictory requirements remain.
