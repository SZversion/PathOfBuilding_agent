# Agent Orchestration

## Flow

```text
user question
  → external AI JSON plan
  → Bridge validates plan and revision
  → local Tool / RAG / approved search execution
  → PoB recalculation and Evidence Graph
  → external AI final Korean answer
```

The external AI can plan multiple sequential operations, but one request is capped at eight Tool/search steps and duplicate identical calls are rejected. The Bridge executes each step and feeds its structured result into the next step.

## Search order

PoB output and breakdown are authoritative for current-build numbers. Local RAG supplies English canonical rules and aliases. If local evidence is insufficient, `search_external` performs direct HTTPS requests from the local Bridge without opening a browser. PoE Wiki uses its MediaWiki search API and page parser. PoEDB currently has no documented general content-search API; the Bridge downloads the same public English autocomplete index used by PoEDB's site UI, ranks matching titles locally, and fetches selected pages directly. Only `poewiki.net` and `poedb.tw`/its CDN are allowed. Results include up to three pages per source and 12,000 page-body characters per result, remain session-only temporary evidence, and are not promoted to the knowledge base.

## Answer contract

The final answer separates calculated values, applied effects, rules, sources, and uncertainty. It is Korean by default. Missing user context triggers a question; missing evidence after allowed search rejects a definitive answer.


## Local function tracing

The local Langfuse service is exposed at `http://localhost:13000`; Compose
services use `http://langfuse-web:3000`. HTTP requests, the CLI subprocess,
AgentLoop, model providers, parsing and validation, execution, MCP dispatch,
and Python PoB transport/handler calls share a run ID and parent span context.
The CLI environment and MCP request headers propagate that context.

Request-scoped tracing records each executed project Python function under
its qualified name. Input contains the complete bound arguments, including
keyword/default arguments. Output contains `return`, all `exceptions`
(including handled failures), and generator `yields` when applicable. Nested
JSON fields, arrays, empty values, and long strings are preserved. Objects
are serialized through their model data or attributes; bound receivers
(`self`/`cls`), cycles, and native runtime handles are represented by identifiers
and types, without copying unrelated receiver state. Tracing infrastructure is excluded
to avoid tracing itself. Third-party library internals and Lua function locals
are not instrumented; the Python transport records the PoB request/response
boundary. Function locals are not collected.

Functions are traced during execution, with actual call nesting and elapsed
time; coroutine awaits and generator yields do not end the function span.
MCP worker calls retain the request context. LLM provider function returns and
`provider_completed` both expose model output; model output is recorded even
when later JSON validation or Tool execution rejects the request. Tool and
final lifecycle events also retain their full result or error payload.

Authentication fields, configured credentials, and authentication/cookie
headers are redacted. A trace failure must not change the function result or
exception. When the SDK/configuration is unavailable, full function payloads
use the existing bounded local queue. An unfinished function at request termination is marked
`incomplete`; tracing warnings remain on the pipeline span. Earlier traces
are not rewritten.
