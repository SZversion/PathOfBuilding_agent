# Agent Execution Trace Plan

## Goal

Make one Agent request reconstructable: when it arrived, which provider and
model handled it, what plan and Tool order ran, what failed or retried, and why
the final outcome was returned.

## In scope

- A common `agent/orchestration/trace.py` recorder and event schema.
- AgentLoop lifecycle events for provider, planner, Tool, final answer, and run.
- Request/run IDs, UTC timestamps, monotonic duration, stage status, attempt,
  retry, timeout, error-code references, snapshot revision, and build ID.
- Provider metadata with mode/model and a redacted endpoint identifier or hash.
- Redacted prompt hash and normalized plan/Tool order with safe arguments.
- Stable references to facts, trace, sources, and Evidence Graph; do not copy
  complete Tool results into the execution log.
- Token counts only when the provider returns them; otherwise `unavailable`.
- Tests for success, retry, timeout, schema error, Tool failure, rejection, and
  sensitive-data redaction.

## Event contract

Every event is a JSON object with these required fields:

```json
{
  "schema_version": "1.0",
  "event_id": "evt-...",
  "run_id": "run-...",
  "request_id": "req-...",
  "event": "run_started|provider_started|provider_completed|provider_failed|planner_started|planner_completed|planner_failed|tool_started|tool_completed|tool_failed|final_started|final_completed|final_failed|run_completed",
  "stage": "run|provider|planner|tool|final",
  "timestamp_utc": "...Z",
  "duration_ms": null,
  "status": "started|ok|partial|failed|rejected|timeout",
  "attempt": 1,
  "provider": {"mode": null, "model": null, "endpoint_ref": null},
  "snapshot": {"revision": null, "build_id": null},
  "tool": null,
  "step_index": null,
  "tool_call_count": null,
  "retry_of": null,
  "plan_ref": null,
  "safe_args_ref": null,
  "error_ref": null,
  "result_ref": {"facts_ref": null, "trace_ref": null, "sources_ref": null, "evidence_graph_ref": null}
}
```

`provider_started/completed/failed`, `planner_started/completed/failed`,
`tool_started/completed/failed`, `final_started/completed/failed`,
`run_started`, and `run_completed` are the minimum lifecycle events. Retry and
the global Tool-call count are recorded as fields/events, not inferred later.

## Storage and privacy

- MVP Trace is memory-only and scoped to one Agent run. No Trace file is
  written by default, so process/session disposal removes it automatically.
- A run is bounded to 256 events and 1 MiB; overflow produces a local warning
  event and keeps the earliest lifecycle/error events. The terminal
  `run_completed` or final failure event is reserved and must never be removed.
- No external server receives the Trace record. The model receives only the
  existing safe response envelope and stable evidence references.
- Never store or emit API keys, Authorization headers, raw XML, complete
  snapshots, user notes, full prompts, itemText, or free-form Tool arguments.
  Keep only redacted hashes, type/length metadata, and normalized safe fields.
- Endpoint values are redacted or hashed. Token values are recorded only when
  explicitly returned by the Provider; never estimate them.

## Out of scope

- UI/log viewer, persistent server storage, disk trace cache, retention controls,
  RAG or PoB calculation changes, Tool semantics, mutation behavior, and remote
  protocol changes.
- Changing `defaultMode=remote` or the development-only Ollama policy.

## Acceptance criteria

1. A fake-provider/fake-Tool run reconstructs the complete lifecycle and final
   outcome from its Trace alone.
2. Normal, retry, timeout, schema-error, Tool-failure, and rejected runs have
   the correct event/status/error references.
3. `request_id`, `run_id`, timestamps, duration, provider metadata, snapshot
   references, plan/Tool order, and final outcome are present.
4. API keys, raw XML, snapshots, prompts, notes, itemText, and free-form Tool
   arguments do not appear in Trace or logs.
5. Existing response envelopes, Evidence Graph/source references, remote
   default, and Ollama dev-only behavior remain unchanged.
6. Trace recorder failure is fail-safe: it cannot stop PoB calculation or the
   final answer; it emits an in-memory warning instead.

## Verification evidence

- Focused Trace schema/redaction/lifecycle tests.
- AgentLoop integration tests for every terminal path and retry accounting.
- Full Python regression suite, Bridge/Lua tests, and `git diff --check`.
- Product-planner review and boundary QA with no blocking finding.
