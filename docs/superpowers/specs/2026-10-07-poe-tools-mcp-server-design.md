# PoE Tool MCP Server Design

## Goal and operating model

Move the project's 32 registered AgentLoop tools behind a local MCP server. The backend remains the only MCP client: it starts the MCP server as a child process using stdio, discovers its tools, passes the tool catalog to the LLM planner, invokes requested tools, and returns results to the LLM. No browser UI is opened and the MCP server does not listen on a network interface.

The MCP server is a local tool adapter, not an LLM host. It delegates existing behavior to project handlers and the running PoB Lua process. Tool names remain the existing canonical snake_case names, and each result preserves the existing JSON facts/error envelope.

## Tool coverage

Expose exactly the current 32 names in `agent/orchestration/agent_loop.py`'s `ALLOWED_TOOLS`:

- PoB read-only tools (24): `get_character_stats`, `get_skill_stats`, `get_skill_dps`, `get_highest_dps_skill`, `get_skill_breakdown`, `get_item_modifiers`, `get_projectile_behavior`, `get_trigger_sequence`, `get_curse_application_order`, `get_ailment_effect`, `get_damage_breakdown`, `get_conversion_chain`, `get_effective_resistance`, `get_support_links`, `resolve_skill_context`, `get_projectile_count`, `get_curse_limit`, `get_elemental_penetration`, `get_skill_chain`, `get_socket_order`, `compare_support_effect`, `explain_damage_change`, `get_duration`, and `explain_stat`.
- Local knowledge tools (3): `search_knowledge`, `resolve_item_alias`, `resolve_skill_alias`.
- External reference search (1): `search_external` (PoE Wiki and PoEDB).
- Snapshot comparison (1): `compare_build_states`.
- Mutation tools (3): `replace_item`, `replace_gem`, `change_passive`.

The MCP registry must match `ALLOWED_TOOLS` exactly; tests fail on missing, extra, or duplicate names. Tool input schemas are derived from the project's argument contracts and validated again at the server boundary. The backend uses the MCP-discovered tool descriptions/schemas when preparing LLM tool choices, while the existing AgentLoop plan validation remains authoritative for execution policy and the eight-call budget.

## Execution boundaries

- The MCP server owns local search and alias handlers, external search, snapshot comparison, and handler routing. It reuses the existing `KnowledgeSearch`, `ExternalSearch`, and Python bridge implementations rather than duplicating their algorithms.
- PoB read-only calls are sent through the existing authenticated `LivePobTransport` to the running PoB process. The Lua `AgentControl` loop dispatches the 24 allowlisted read-only tools through `AgentInProcess` and `AgentBridge`; all execution touching PoB memory stays on PoB's UI thread.
- The MCP server exposes the fresh normalized PoB context as resource `pob://current-snapshot`. Before an LLM turn, the backend reads this resource and sends only the normalized snapshot to the model. Each PoB tool call observes/captures the active context and returns its revision and evidence envelope.
- `compare_build_states` delegates to the existing comparison implementation using the supplied snapshots; it does not load a build file or mutate PoB state.
- `search_external` remains code-only HTTPS/API access with its current source allowlist and content limits; no browser automation is introduced.
- Mutation tools remain registered and visible, but the MCP adapter never routes them through the one-shot headless XML adapter. Until the live in-process dispatcher advertises mutation capability, calls return the existing structured `MUTATION_NOT_PERSISTENT` rejection with no side effect. No save or Save As is performed.

## Protocol and failures

- The backend starts one MCP stdio session per backend runtime and reuses it for requests. MCP protocol messages use stdin/stdout only; diagnostics go to stderr.
- The MCP server reads the PoB endpoint metadata and capability token from the existing per-process endpoint file and uses `LivePobTransport`'s `op` request contract. It does not expose the token to the LLM, tool result, or logs.
- Each MCP tool returns one JSON-serialized result content block so the backend can feed the existing envelope into the AgentLoop without shape loss. Tool failures remain structured project errors; MCP startup/transport failures become `HANDLER_NOT_CONFIGURED`/bridge-unavailable errors and do not trigger an automatic headless fallback.
- If PoB is closed, lacks an active build, or changes state during a request, return the corresponding live bridge error/revision and let existing stale-revision policy reject unsafe work.

## Acceptance criteria

1. A backend can launch the local MCP server over stdio, list all 32 tools, and invoke each supported handler through MCP.
2. The backend can read `pob://current-snapshot` and receives the current normalized live context and revision without reading build files itself.
3. The MCP tool list and AgentLoop allowlist have exact set equality; every registered tool has a schema and description.
4. The 24 PoB read-only tools can be dispatched through the authenticated local socket without opening/reloading a build file; UI state remains authoritative.
5. Knowledge search, alias resolution, external search, and snapshot comparison use the existing code paths and preserve their established result contracts.
6. Mutation tool calls are discoverable but rejected with `MUTATION_NOT_PERSISTENT` until live mutation is supported; they do not modify or save a build.
7. Stdio framing remains valid, diagnostics never pollute stdout, and process/PoB unavailability produces structured errors.
8. Existing test suite, catalog lint, Lua checks, and MCP end-to-end smoke tests pass.

## Explicit assumptions

- Backend and MCP server run on the same PC; backend is the only MCP client.
- The local MCP transport is stdio; remote Streamable HTTP deployment is out of scope.
- “All implemented tools” means the exact current 32-name AgentLoop registry, including registered mutation contracts with their existing live capability rejection.
- Existing uncommitted live-control and tool changes in the current checkout are part of the implementation baseline and must be preserved.
