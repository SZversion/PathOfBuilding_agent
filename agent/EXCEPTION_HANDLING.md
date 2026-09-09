# Agent Exception Handling and Failure Contract

This document defines how the PoB Agent classifies, reports, retries, and escalates failures. It applies to the external LLM plan, local Bridge, PoB Tools, RAG, and final-answer pipeline.

## 1. Non-negotiable rules

1. Never hide a failure behind a guessed value.
2. Every failure has a stable `code`, `stage`, `retryable` flag, and structured detail.
3. Internal Bridge and Tool responses are pure JSON; no prose or Markdown is accepted.
4. A valid JSON document is not automatically a valid or correct answer. Schema, grounding, and business-rule checks are separate.
5. Observed facts and remediation decisions are stored separately.
6. A retry must use the failure class to choose its repair prompt or action; generic “try again” is forbidden.
7. Retry exhaustion is a normal terminal state and is routed to rejection or human review.

## 2. Recovery hierarchy

The Agent chooses the recovery action from the parent class first. The detailed error code explains the cause inside that class.

```text
failure
├─ RETRY_LLM          → repair the model output and retry
├─ RETRY_TOOL         → retry the PoB/search/model dependency within a limit
├─ REPAIR_INPUT       → fix arguments or planner output locally
├─ REFRESH_CONTEXT    → recapture PoB state, version, or RAG context
├─ ASK_USER           → request missing or ambiguous user information
├─ REJECT             → stop because a safe answer is impossible
├─ HUMAN_REVIEW       → technical checks passed but approval is required
└─ FATAL_INTERNAL     → record the defect and stop the run
```

`recovery_class` is the routing key. `code` is the diagnostic key. The same recovery class may contain many detailed codes. Exactly one `recovery_class` is primary for each failure; any additional observations are recorded as `secondary_causes` and never used as competing routing instructions. Resolution priority is: safety/contract failure, stale context, missing user input, dependency retry, then rejection/escalation. A registry entry, not a free-form message, assigns the primary class.

| recovery_class | Typical codes | Automatic action |
|---|---|---|
| `RETRY_LLM` | `NO_JSON`, `JSON_DECODE`, `SCHEMA_VIOLATION` | Send a targeted repair prompt |
| `RETRY_TOOL` | `TIMEOUT`, `SEARCH_TRANSIENT`, `MODEL_TRANSIENT` | Retry with bounded backoff |
| `REPAIR_INPUT` | `INPUT_INVALID`, `TOOL_NOT_FOUND`, `CONTENT_CONFLICT` | Repair or reject the plan locally |
| `REFRESH_CONTEXT` | `SNAPSHOT_REVISION_CONFLICT` | Recapture state or rebuild context |
| `ASK_USER` | `USER_CONTEXT_MISSING`, `AMBIGUOUS_ALIAS` | Ask one focused question |
| `REJECT` | `GROUNDING_MISSING`, `GROUNDING_CONFLICT`, `VERSION_MISMATCH`, `VALUE_UNAVAILABLE` | Return a safe non-answer |
| `HUMAN_REVIEW` | policy approval boundary, retry ceiling reached | Queue evidence and stop automation |
| `FATAL_INTERNAL` | `INTERNAL_INVARIANT_VIOLATION`, `UNCLASSIFIED_FAILURE` | Stop and retain diagnostic trace |

The parent class is never inferred from a free-form message. It is assigned by a deterministic error-code registry.

### 2.1 Stable recovery and leaf-code registry

The following registry is the minimum stable vocabulary. New leaf codes must be added here before they are emitted. `UNCLASSIFIED_FAILURE` is the mandatory fallback for an unknown code and always maps to `FATAL_INTERNAL`; it must never be silently treated as retryable.

| recovery_class | Stable leaf codes |
|---|---|
| `RETRY_LLM` | `NO_JSON`, `JSON_DECODE`, `SCHEMA_VIOLATION`, `LLM_CONTENT_REPAIRABLE` |
| `RETRY_TOOL` | `TIMEOUT`, `SEARCH_TRANSIENT`, `MODEL_TRANSIENT`, `TOOL_TRANSIENT`, `RAG_TRANSIENT`, `RAG_UNAVAILABLE` |
| `REPAIR_INPUT` | `INPUT_INVALID`, `TOOL_NOT_FOUND`, `CONTENT_CONFLICT`, `INVALID_MUTATION_PLAN` |
| `REFRESH_CONTEXT` | `SNAPSHOT_REVISION_CONFLICT`, `STALE_CACHE`, `VERSION_STALE`, `POB_STATE_CHANGED`, `DIFF_UNTRUSTED`, `CONTEXT_RECAPTURE_FAILED`, `MUTATION_TIMEOUT`, `MUTATION_UNCERTAIN` |
| `ASK_USER` | `USER_CONTEXT_MISSING`, `AMBIGUOUS_ALIAS`, `USER_CONFIRMATION_REQUIRED` |
| `REJECT` | `GROUNDING_MISSING`, `GROUNDING_CONFLICT`, `VERSION_MISMATCH`, `VALUE_UNAVAILABLE`, `BUILD_LOAD_FAILED`, `SEARCH_POLICY_DENIED`, `MUTATION_FAILED`, `MUTATION_NOT_PERSISTENT`, `RETRY_EXHAUSTED` |
| `HUMAN_REVIEW` | `HUMAN_REVIEW_REQUIRED`, `RETRY_BUDGET_EXHAUSTED`, `POLICY_APPROVAL_REQUIRED`, `UNRESOLVED_EVIDENCE_CONFLICT` |
| `FATAL_INTERNAL` | `INTERNAL_INVARIANT_VIOLATION`, `POB_CALCULATION_ERROR`, `BRIDGE_PROTOCOL_ERROR`, `UNCLASSIFIED_FAILURE` |

`VERSION_WARNING` is a stable leaf code under the successful/continuable path, not a recovery class: it records a same-major minor/patch mismatch and maps to `status: partial` or `ok` with an explicit warning. It must not be confused with `VERSION_MISMATCH`, which maps to `REJECT`.

`VERSION_WARNING` belongs to the warning registry, not the error registry. Warning records still contain `code: VERSION_WARNING`, `stage`, `details`, and `next_action`, but do not contain an error `recovery_class`. Every emitted error code, by contrast, must appear in the error registry above and have exactly one primary `recovery_class`.

`HUMAN_REVIEW` is for an operator or maintainer queue. `ASK_USER` is for a missing decision or fact that the end user can provide; it must never expose internal diagnostics as a request for the user to repair the system. `FATAL_INTERNAL` retains detailed internal traces but exposes only a sanitized user message.

## 3. Output contract

Every internal result uses this envelope:

```json
{
  "schema_version": "1.0",
  "status": "ok|partial|unavailable|timeout|rejected|human_review|error",
  "snapshotRevision": "rev-123",
  "side_effect": "none|in_memory|persisted|unknown",
  "operator_message": null,
  "facts": {},
  "trace": [],
  "sources": [],
  "version": {"gamePatch": null, "pobVersion": null, "dataRevision": null},
  "evidenceGraph": {"nodes": [], "stages": [], "sourceEdges": []},
  "uncertainty": {"level": "none|low|medium|high", "reasons": [], "missingEvidence": []},
  "error": null
}
```

When `status` is not `ok`, `error` is required:

```json
{
  "code": "NO_JSON",
  "recovery_class": "RETRY_LLM",
  "stage": "parse",
  "retryable": true,
  "attempt": 1,
  "max_attempts": 2,
  "message": "No JSON object was found in the model response.",
  "details": {},
  "next_action": "repair_llm_output",
  "secondary_causes": [],
  "side_effect": "none",
  "operator_message": null
}
```

`error.code` and `error.recovery_class` are the canonical locations in the envelope. They must not be duplicated as unrelated top-level fields. `secondary_causes` contains observed contributing codes only; it cannot override the primary routing class.

Fixed keys, explicit types, enums, defaults, examples, and JSON-only transport are mandatory. Free-form human explanations belong only in the final Korean response.

## 3. Failure stages and codes

### 3.1 LLM output contract

| Code | Meaning | Default action |
|---|---|---|
| `NO_JSON` | No JSON object exists | Retry with JSON-only instruction |
| `JSON_DECODE` | JSON syntax is invalid | Retry with parser error and raw boundary |
| `SCHEMA_VIOLATION` | Keys, types, enum, or range violate contract | Retry with field-level errors |
| `CONTENT_CONFLICT` | Fields are individually valid but logically inconsistent | Do not blindly retry; run grounding/business check |

### 3.2 Grounding and evidence

| Code | Meaning | Default action |
|---|---|---|
| `GROUNDING_MISSING` | Required PoB/RAG/source evidence is absent | Search or call Tool; otherwise reject |
| `GROUNDING_CONFLICT` | Sources disagree | Preserve both sources and reject a definitive value |
| `VERSION_MISMATCH` | Game/PoB major version is incompatible | Reject |
| `VERSION_WARNING` | Same-major minor/patch mismatch | Continue with warning or cached result |
| `USER_CONTEXT_MISSING` | Skill, Skill Set, Config, or comparison target is unspecified | Ask the user |

### 3.3 PoB Bridge and Tool execution

| Code | Meaning | Default action |
|---|---|---|
| `BUILD_LOAD_FAILED` | XML or normalized snapshot cannot be loaded | Reject the request; do not mutate state |
| `INPUT_INVALID` | Tool argument is missing or wrong type | Reject locally; do not call PoB |
| `VALUE_UNAVAILABLE` | PoB loaded the build but the requested output does not exist | Return `unavailable` and expose the exact output path |
| `TIMEOUT` | PoB calculation exceeded the configured deadline | Cancel the current calculation request, discard its execution context, then allow one bounded retry |
| `TOOL_NOT_FOUND` | Requested Tool is not registered | Return error and mark planner/tool catalog mismatch |
| `POB_CALCULATION_ERROR` | PoB calculation raised an internal error | Return error with PoB message and trace |
| `SNAPSHOT_REVISION_CONFLICT` | User changed PoB state during an Agent mutation | Discard mutation and recapture the current snapshot |
| `MUTATION_FAILED` | Requested item/gem/passive change was not applied | Restore prior in-memory state and report rejection |

### 3.4 External dependencies

| Code | Meaning | Default action |
|---|---|---|
| `RAG_UNAVAILABLE` | Local index cannot be loaded or queried | Primary class is always `RETRY_TOOL`; use the PoB-only path when PoB evidence is sufficient, otherwise finish with `REJECT` after the bounded retry policy |
| `SEARCH_TRANSIENT` | Approved external search returned a transient failure | Retry once, then mark temporary evidence unavailable |
| `SEARCH_POLICY_DENIED` | Domain or query is not approved | Do not retry; reject that evidence path |
| `MODEL_TRANSIENT` | External model/API timeout, rate limit, or 5xx | Retry with bounded backoff, then human review/error |

Unknown or unregistered codes are normalized to `UNCLASSIFIED_FAILURE` → `FATAL_INTERNAL` and are never sent to an automatic retry loop.

## 4. Validation pipeline

Validation runs in this order and stops at the first failed gate:

```text
raw response
  → parse (NO_JSON / JSON_DECODE)
  → schema (SCHEMA_VIOLATION)
  → content consistency (CONTENT_CONFLICT)
  → grounding/evidence (GROUNDING_*)
  → version policy (VERSION_*)
  → Tool argument validation (INPUT_INVALID)
  → Tool execution (VALUE_UNAVAILABLE / TIMEOUT / POB_CALCULATION_ERROR)
  → mutation/snapshot check
  → final answer contract
```

The validator is deterministic and must be tested with synthetic failures before connecting a model. A successful schema check does not prove that the value is correct.

## 5. Retry and escalation policy

Defaults:

- LLM output repair: maximum 2 LLM attempts total. LLM attempts are tracked separately from Tool calls.
- External model transient failure: maximum 2 LLM attempts with bounded backoff.
- `tool_call_count <= 8` for each user request. This is the single hard limit for PoB, RAG, and approved-search Tool calls; retries are counted in the same total and there is no separate retry allowance.
- Tool timeout/transient failures: one initial attempt plus at most 3 retries (4 total attempts). Each retry cancels/discards the failed execution context before starting the next attempt; the limit is hard and there is no unbounded loop.
- User-input errors (`REPAIR_INPUT`/`ASK_USER`), grounding missing or conflict, snapshot/mutation conflicts, and other non-transient failures are never retried automatically.
- Tool argument or version errors: zero automatic retries; repair the plan or ask the user.
- Grounding failure: at most one additional Tool/search plan, then reject if evidence remains missing.
- `tool_call_count <= 8` is evaluated independently of the LLM attempt limit. Every Tool retry, including RAG and approved-search retries, increments `tool_call_count`. On exhaustion, route to `HUMAN_REVIEW` when an operator can inspect the evidence, otherwise `REJECT`.
- Read/query retries and mutation retries are different. Read/query operations may retry only when their registered code is retryable. A mutation may not be automatically retried unless it carries an idempotency key or the current snapshot revision has been revalidated and the operation is proven safe to repeat.
- A mutation timeout or uncertain result is therefore `REFRESH_CONTEXT` first, followed by recapture and reconciliation; it is not an immediate second mutation.
- `REFRESH_CONTEXT` covers untrusted diffs, stale cache/version, and any PoB state change detected during a request. If recapture or reconciliation fails, route to `REJECT`.
- `RAG_UNAVAILABLE` always keeps primary class `RETRY_TOOL`; after its bounded retry, continue only when PoB evidence alone is sufficient. If PoB evidence is insufficient, terminate with `REJECT` rather than inventing a rule or changing the primary classification retroactively.

Retry records preserve `attempt`, `error.code`, raw response reference, and the changed remedy. A retry that succeeds remains counted as a first-attempt failure for reliability metrics.

After the ceiling:

- technical uncertainty → `rejected` or `unavailable` with a user-safe explanation;
- business approval boundary → `human_review`;
- never silently convert failure to success.

No policy may create an unbounded loop. Every retry decision records the consumed request budget and the next bounded action.

## 6. LLM repair actions

| Failure class | Repair input to LLM |
|---|---|
| `NO_JSON` | Repeat the exact schema and require JSON only |
| `JSON_DECODE` | Include parser location and request corrected JSON only |
| `SCHEMA_VIOLATION` | Include field-level expected type/enum/range |
| `CONTENT_CONFLICT` | Provide the conflicting fields and ask for a consistent plan |
| `GROUNDING_MISSING` | Ask for the missing Tool/RAG query, not a guessed answer |
| `VALUE_UNAVAILABLE` | Ask for an alternate PoB output or explain unavailability |
| `TIMEOUT` | Narrow the request, reduce Tool scope, or ask for user confirmation |

The LLM may not change `schema_version`, bypass required fields, invent a source, or downgrade an error to success.

## 7. Failure taxonomy and metrics

Record two denominators:

- **request-level**: whether the final user request succeeded;
- **attempt-level**: every failed LLM/Tool attempt, including attempts rescued by retry.

Classify operational causes into:

- `OUTPUT_CONTRACT`: parse/schema/contract failures;
- `GROUNDING`: missing or conflicting evidence;
- `TOOL_RELIABILITY`: PoB, RAG, search, model, timeout, or dependency failures;
- `UNCLASSIFIED`: temporary holding category that requires a new taxonomy entry.

`UNCLASSIFIED` is an observability label only; at runtime its stable leaf code is `UNCLASSIFIED_FAILURE` with primary recovery `FATAL_INTERNAL`.

Observed facts (`code`, count, raw reference) are separate from decisions (`owner`, `priority`, `next_action`). Human review is not the same as a JSON or Tool failure.

## 8. PoE-specific safety rules

- PoB-calculated values outrank model reasoning for current-build numbers.
- A missing `TotalDPS`, duration, chain, or other output is `VALUE_UNAVAILABLE`, not zero.
- A major game or PoB version mismatch is rejected.
- Same-major minor/patch mismatch may continue only with an explicit warning.
- `planned`, `draft`, `unverified`, `partial`, `conflict`, and version-unknown rules cannot be sole authoritative evidence.
- Temporary external search evidence must be labeled and cannot silently promote a rule.
- Do not transmit raw LLM responses, raw PoB XML, or user notes outside the local process. External calls receive only the minimum normalized snapshot/diff and redacted identifiers; preserve local references or hashes for internal traceability.
- `FATAL_INTERNAL` keeps detailed trace data in local protected storage, while the user-facing message is sanitized and must not contain stack traces, XML, prompts, credentials, or private notes.

## 9. Required trace fields

Every failure record must preserve:

```json
{
  "run_id": "...",
  "request_id": "...",
  "attempt": 1,
  "stage": "tool_execution",
  "code": "TIMEOUT",
  "recovery_class": "RETRY_TOOL",
  "retryable": true,
  "tool": "get_highest_dps_skill",
  "build_id": "...",
  "gamePatch": "3.29",
  "pobVersion": "...",
  "dataRevision": null,
  "raw_reference": "local trace path or redacted hash",
  "details": {},
  "next_action": "retry_once"
}
```

Sensitive XML contents and user notes are not copied into external model error messages. Use a local reference or redacted hash instead.
