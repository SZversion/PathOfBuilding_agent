# Langfuse Trace Export Plan

## Goal

Export the existing sanitized, run-scoped Agent Trace to a local Langfuse
instance so a request can be inspected without changing PoB calculations,
Tool semantics, or the external-model protocol.

## In scope

- An optional Langfuse exporter attached to the existing TraceRecorder.
- One Agent `run_id`/`request_id` mapped to exactly one Langfuse trace.
- Lifecycle event export with IDs, stages, durations, statuses, provider
  metadata, retry/error references, snapshot/build references, and result refs.
- Configuration from process environment variables only by default:
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`.
- An explicit development opt-in flag; a base URL alone never enables export.
- SDK version support bounded to the tested Langfuse 4.x API. Missing SDK or
  incomplete configuration produces a no-op/unavailable exporter.
- Bounded flush/close timeout and no exporter retries that block AgentLoop.
- Fake SDK and fake HTTP boundary tests plus a real local smoke test when the
  Langfuse service is available.
- Documentation for local setup, retention, and deletion.

## Privacy and security contract

- API keys are used only for authentication and are never placed in events,
  metadata, errors, logs, or user responses.
- Send only existing redacted `prompt_ref`, `safe_args_ref`, `result_ref`,
  lifecycle fields, and non-sensitive provider identifiers.
- Never send raw prompts, XML, complete snapshots, user notes, free-form Tool
  arguments, Authorization headers, or full Tool results.
- `.env` is not read implicitly from an arbitrary working directory. Process
  environment variables take precedence; any `.env` loading must be an
  explicit development-only option with an explicit project-root path.

## Explicit enablement and failure behavior

1. Export is disabled by default and sampling defaults to `0`.
2. Enablement requires an explicit development flag plus all three Langfuse
   variables. Missing or partial configuration returns an unavailable/no-op
   exporter without stopping AgentLoop.
3. SDK import errors, connection errors, malformed responses, flush errors, and
   close errors are isolated from PoB/Agent execution and recorded only as a
   local warning.
4. Flush timeout, close timeout, and close retry count are fixed and bounded;
   exporter shutdown never waits indefinitely.
5. Exporter errors never create a second Agent result or change the result
   status produced by the existing Trace/AgentLoop.

## Langfuse mapping

| Agent Trace | Langfuse field |
|---|---|
| `run_id` | trace id/metadata reference |
| `request_id` | trace metadata |
| event name/stage/status | observation name/type/level |
| `timestamp_utc`/`duration_ms` | observation timing |
| provider mode/model/endpoint ref | redacted metadata |
| attempt/retry/tool budget | observation metadata |
| error ref | observation status/error metadata |
| facts/trace/sources/evidence refs | result reference metadata only |

## Out of scope

- UI viewer, remote Langfuse hosting, automatic `.env` discovery, model or
  provider changes, RAG/PoB/Tool changes, raw prompt logging, persistent Agent
  cache changes, retention enforcement inside the app, and changing the
  production remote default.

## Acceptance criteria

1. Export remains disabled unless explicitly enabled in development.
2. One run creates at most one Langfuse trace and preserves its run/request IDs.
3. Fake SDK/HTTP tests cover success, incomplete config, missing SDK, timeout,
   flush failure, malformed response, and close behavior.
4. A local Langfuse smoke test succeeds when the service is available, or is
   reported as unavailable without being treated as a passing export.
5. Redaction tests prove that keys, Authorization, raw prompt/XML/snapshot,
   notes, free text, and full Tool results never leave the process.
6. Existing Trace/AgentLoop behavior, remote default, Ollama dev-only policy,
   27-test regression suite, and Ollama smoke remain unchanged.

## Verification evidence

- Focused exporter tests and privacy tests.
- Full Python regression, PoB Bridge/Lua tests, and diff check.
- Local Langfuse smoke result with exact command and status.
- Product-planner review and boundary QA with no blocking finding.
