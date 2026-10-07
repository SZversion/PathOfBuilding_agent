# PoE MCP Tool Design Redesign

## Basis and scope

The supplied course directory contains a README that identifies lessons 06–09 as covering four tool-design principles, `tool_description`, errors/timeouts, and multi-tool use. The lesson notebooks themselves are absent. This design therefore uses that published outline as the course basis and the repository's `agent/TOOL_AUTHORING.md`, `agent/TOOL_TESTING.md`, exception registry, and response-envelope contract as the concrete project rules. It does not claim to reproduce the missing lesson's exact four principles.

Redesign the contracts and MCP exposure of the existing 32 tools. Keep all canonical tool names and the local stdio architecture. Do not add a browser, a remote MCP listener, new game-calculation logic, or live mutation capability.

## Selected approach

Preserve the current 32 names and improve their contracts in place. A versioned rename or a single broad `poe_query` tool would break existing planner behavior and make selection less precise. A descriptions-only pass would leave argument, error, and timeout behavior ambiguous. Implementation groups remain routing metadata; each tool also receives a separate semantic category.

## Tool contract

Each catalog entry is one cohesive public operation and records:

- canonical name and semantic category (`context_resolution`, `state_metadata`, `calculation`, `trace_evidence`, `comparison_simulation`, `mutation`, or `knowledge_search`);
- a model-facing description stating purpose, when to use it, required context, key constraints, and result shape;
- a JSON Schema with field-level descriptions, types, requiredness, bounds, enums, and defaults where applicable;
- result facts/shape, side effect, idempotency, bounded timeout, retry policy, error codes, and one representative example;
- implementation provider group, kept separate from semantic category.

MCP descriptions are rendered from these structured fields. MCP annotations report read-only/destructive/idempotent/open-world behavior. Tool names and signatures remain stable unless a separately reviewed compatibility change is approved.

## Composition and failure behavior

Keep tools small and composable. The AgentLoop planner composes existing operations sequentially, with its existing eight-call ceiling and revision checks; the MCP server does not hide multiple unrelated operations behind one call. The planner receives the discovered read-only schemas and descriptions.

All successful tool calls return the project's common result envelope. Existing PoB facts, paths, traces, conditions, source edges, version fields, precision, and `snapshotRevision` are preserved. Knowledge and external-search payloads are placed in `facts` and retain their source and temporary-evidence markings. Failures use the registered leaf code, its parent `error_ref`, one `recovery_class`, stage, retryability, attempt bounds, and safe details. MCP `isError` is set for failures; the backend converts these into structured AgentLoop step errors, so a transport failure is not counted as a successful result. Unknown failures map to `UNCLASSIFIED_FAILURE` and are never retried.

Timeout/retry policy is explicit per tool. Only idempotent read-only calls with a registered transient code may retry, within the existing per-request tool budget. Mutations have no retry and remain rejected as `MUTATION_NOT_PERSISTENT` before any bridge call.

## Source of truth and extensibility

`agent/tool_catalog.py` remains the executable source of each tool's complete contract. `ALLOWED_TOOLS`, MCP definitions, planner metadata, and generated MCP documentation derive from it. `docs/tools/catalog.md` remains the human-readable authority for PoB paths, fixture evidence, and promotion status; a generated section covers the executable schema and description. `agent/TOOL_AUTHORING.md` will distinguish these roles.

Adding a tool requires one contract record, one implementation in its provider group, relevant PoB Lua capability registration when applicable, and tests for schema, description, result/error envelope, timeout/retry semantics, and an appropriate composition path. Catalog lint checks documented and executable membership, category/group validity, and Lua allowlist parity.

## Acceptance criteria

1. All 32 existing names remain available, each with a semantic category and complete model-facing description.
2. Every exposed argument has an accurate field description and executable validation; required context and bounds agree with dispatch behavior.
3. Every handler returns the common success/error contract without losing existing PoB evidence or external-source markings.
4. Error codes and recovery classes come from the existing registry; retry and timeout rules are machine-readable and bounded.
5. MCP tool annotations match actual side effects; the three mutation tools remain discoverable but cannot reach a mutation adapter.
6. Planner composition remains sequential, revision-aware, limited to eight calls, and based on MCP-discovered read-only schemas.
7. Generated documentation, Python catalog, AgentLoop allowlist, MCP list, and 24 Lua PoB operations are checked for parity.
8. Unit, stdio, planner, CLI, and Lua checks pass. Live PoB verification remains separately identified when the installed PoB process has not loaded the new Lua dispatcher.
