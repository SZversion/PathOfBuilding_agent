# Langfuse Trace Export Plan

The original opt-in policy below has been updated to default local tracing.
The current host URL is `http://localhost:13000` (`LANGFUSE_PORT=13000` in
`.env.docker`). The Docker backend uses `http://langfuse-web:3000` with
`POB_AGENT_LANGFUSE_ALLOWED_HOSTS=langfuse-web`; the container port remains
`3000`. A backend running directly on the host uses
`LANGFUSE_BASE_URL=http://localhost:13000`. Remote Langfuse is out of scope.

## Goal

Export the existing sanitized, run-scoped Agent Trace to a local Langfuse
instance so a request can be inspected without changing PoB calculations,
Tool semantics, or the external-model protocol.

## In scope

- A default Langfuse exporter attached to the existing TraceRecorder.
- One Agent `run_id`/`request_id` mapped to exactly one Langfuse trace.
- Lifecycle event export with IDs, stages, durations, statuses, provider
  metadata, retry/error references, snapshot/build references, and result refs.
- Configuration from process environment variables, supplemented by the
  repository-root `.env` when a value is absent:
  `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`.
- No development opt-in flag; sampling defaults to `1`. Missing credentials
  or SDK keep tracing in local queue mode.
- SDK version support bounded to the tested Langfuse 4.x API. Missing SDK or
  incomplete configuration produces a queue-only exporter.
- Bounded flush/close timeout and no exporter retries that block AgentLoop.
- Fake SDK and fake HTTP boundary tests plus a real local smoke test when the
  Langfuse service is available.
- Documentation for local setup, retention, and deletion.

## Privacy and security contract

- API keys are used only for authentication and are never placed in events,
  metadata, errors, logs, or user responses.
- Local Langfuse records complete LLM response JSON (including retries) and
  the complete AgentLoop response JSON. Root and terminal outputs contain
  `llm_outputs` and `response`; JSON objects, arrays, empty values, and nested
  fields are preserved. Valid JSON model responses are stored as objects.
- Authentication fields and configured credential values are redacted before
  SDK export or queue persistence. This does not authorize sending raw XML
  or sending payloads to remote Langfuse services.
- Span start/end times reflect original event timestamps, not export time.
- `.env` is read only from the repository root, not an arbitrary working
  directory. Process environment variables take precedence.

## Default enablement and failure behavior

1. Tracing is wired by default and sampling defaults to `1`.
2. Sending requires all three Langfuse variables, an available SDK, and a
   local endpoint. Loopback hosts are allowed by default; the Docker service
   `langfuse-web` requires the explicit allowed-host setting above. Missing or
   partial configuration queues redacted events without stopping AgentLoop.
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
  provider changes, RAG/PoB/Tool changes, additional raw XML capture, persistent Agent
  cache changes, retention enforcement inside the app, and changing the
  production remote default.

## Acceptance criteria

1. AgentLoop attempts export by default with sampling `1`; incomplete
   configuration or service failures preserve redacted events in the bounded
   local queue.
2. One run creates at most one Langfuse trace and preserves its run/request IDs.
3. Fake SDK/HTTP tests cover success, incomplete config, missing SDK, timeout,
   flush failure, malformed response, and close behavior.
4. A local Langfuse smoke test succeeds when the service is available, or is
   reported as unavailable without being treated as a passing export.
5. Redaction tests prove that credentials and Authorization values never
   leave the process. Tests preserve all non-credential JSON response fields,
   including nested objects, arrays, empty values, retries, and error details.
   Real-service verification confirms original span timestamps and duration.
6. Existing Trace/AgentLoop behavior, remote default, Ollama dev-only policy,
   27-test regression suite, and Ollama smoke remain unchanged.

## Verification evidence

- Focused exporter tests and privacy tests.
- Full Python regression, PoB Bridge/Lua tests, and diff check.
- Local Langfuse smoke result with exact command and status.
- Product-planner review and boundary QA with no blocking finding.
