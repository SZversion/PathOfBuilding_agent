# Ollama JSON Planner Integration Plan

**Goal:** Route the configured Ollama model through its native provider so the planner's existing JSON schema is enforced.

**Architecture:** Select the provider explicitly from `POB_AGENT_MODEL_PROVIDER`. Reuse `PLANNER_JSON_SCHEMA` and `OllamaDevelopmentProvider`, propagating the configured endpoint and model from the HTTP backend environment.

**Tech Stack:** Python CLI, Ollama `/api/chat`, Docker Compose environment.

## Tasks

- [x] Add explicit Ollama/OpenAI-compatible selection to CLI provider creation; pass configured endpoint and model to Ollama.
- [x] Pass provider selector through Docker Compose and configure the local example and current `.env.docker` to use `qwen3:8b`.
- [x] Review the diff and manually verify the running HTTP streaming path against local Ollama.

**Verification result:** The HTTP endpoint returned 200 and streamed 63 token events with the configured `qwen3:8b` provider. The run ended `partial`, so a successful complete PoB answer is not confirmed; this check confirms provider selection and token streaming only.

## Constraints

- Keep OpenAI-compatible provider as the default when no provider is configured.
- Do not log model prompts, raw responses, credentials, or build XML.
- Reuse the existing planner schema and validation.
