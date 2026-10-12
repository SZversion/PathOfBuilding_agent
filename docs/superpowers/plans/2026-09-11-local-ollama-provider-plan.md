# Local Ollama Development Provider Plan

## Goal

Enable an explicitly selected development-only Ollama provider for `qwen3:8b`
through the existing structured AgentLoop contract, while keeping the
production default and external-server policy unchanged.

## In scope

- A local Ollama provider/adapter using the OpenAI-compatible `/v1` endpoint.
- Explicit development-mode provider selection and configuration validation.
- Default endpoint `http://127.0.0.1:11434/v1` and configurable model,
  defaulting to `qwen3:8b`.
- Reuse of the existing structured request, response, retry, and error envelope.
- Provider unit/integration tests and an environment-dependent Ollama smoke test.
- Provider configuration documentation and examples.
- Registration or normalization of every emitted model error code in the error
  registry, including existing `MODEL_REQUEST_FAILED` and
  `MODEL_SCHEMA_INVALID` behavior.

## Out of scope

- Changing `defaultMode=remote` or adding automatic remote fallback.
- User-facing model download, model installation, or model update UI.
- RAG, PoB Bridge, Tool, mutation, snapshot, or UI changes.
- Native Ollama API support; only the OpenAI-compatible `/v1` contract is used.
- Fine-tuning or packaging Ollama as a dependency.

## Rules and acceptance criteria

1. Production configuration always selects `remote`.
2. A local endpoint is accepted only when an explicit development mode is
   enabled; production rejects it even if `local.enabled=true`.
3. Local provider selection is explicit and never an automatic fallback.
4. `qwen3:8b` is passed as the model unless a development override is supplied.
5. Malformed response, timeout, unavailable service, and HTTP errors map to
   registered error codes and the existing envelope.
6. Ollama absence is reported as `skipped`/`unavailable`, not as a passing
   production test.
7. API keys, raw XML, snapshots, and prompts are not written to provider logs.
8. Existing remote provider tests and behavior remain unchanged.

## Verification evidence

- Focused provider/config tests.
- Error mapping, timeout, malformed response, and production-guard tests.
- Existing full Python regression suite.
- Real `qwen3:8b` Ollama smoke test when the service is installed; otherwise an
  explicit skipped result with the reason.
- Product-planner review against this plan.
- QA through the provider boundary, including remote regression and log checks.

## Risks

- A local endpoint could bypass production safeguards.
- Local failures could silently fall back to remote or emit unregistered codes.
- A successful local smoke test could be mistaken for production support.

## Gate exit

Do not report completion until implementation, focused tests, regression tests,
product review, and boundary QA all have recorded evidence and no blocking
finding remains.
