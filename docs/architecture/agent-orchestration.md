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


## Local pipeline tracing

The local Langfuse service is exposed at `http://localhost:13000`; Compose
services use `http://langfuse-web:3000`. HTTP requests, the CLI subprocess,
AgentLoop, and MCP calls share a run ID and parent span context through the
CLI environment and MCP request headers.

Trace observations cover major stages instead of every Python function:
request validation, MCP connection and tool discovery, snapshot capture,
query normalization, snapshot preparation, plan validation, plan execution,
and individual tool calls. HTTP/streaming and CLI pipeline spans group these
stages. A normal single-tool request has approximately 10–15 observations;
early failures have fewer, and additional tool calls or model retries may
have more. MCP server callbacks propagate the client context without creating
duplicate server/protocol observations. Helper functions, comprehensions,
token callbacks, and duplicated lifecycle events are not separate spans.

Every executed LLM provider `chat` or `stream_chat` call is a Langfuse
`generation` observation named `generate`, with the model name, complete
messages, model output, actual elapsed time, and exceptions. Streaming chunks
are joined into the complete output. Planner JSON remains visible when plan
validation rejects it; failed calls and retries remain separate generations.
Stages that did not execute are not fabricated. Standalone lifecycle exports
also represent completed/failed provider calls as generations.

Selected stages retain their complete bound arguments and return/error
payloads, including nested JSON fields, arrays, and empty values. Root output
retains `llm_outputs` and the complete AgentLoop `response`. The returned
application trace event list is unchanged. Authentication fields, configured
credentials, and authentication/cookie headers are redacted.

Trace failures must not change application results or exceptions. The existing
bounded local queue retains stage inputs, outputs, generation type, and model
metadata if the SDK/service is unavailable. Unfinished stages are marked
`incomplete`. Earlier traces are not rewritten.
