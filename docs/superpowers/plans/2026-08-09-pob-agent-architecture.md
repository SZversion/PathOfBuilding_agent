# PoB Agent Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a maintainable Agent boundary to the PoB fork with online API as the default model path and optional user-installed local models.

**Architecture:** Keep PoB Lua as the source of deterministic build calculations. Add a small PoB bridge for structured facts and a separate Agent runtime for orchestration, RAG, provider selection, and model management. The runtime supports user-provided online API keys stored in Windows Credential Manager and an optional local Qwen/llama.cpp installation.

**Tech Stack:** Existing PoB Lua/runtime; Agent sidecar with a small typed protocol; JSON knowledge/tool schemas; Windows Credential Manager/DPAPI; llama.cpp-compatible local model adapter; provider adapters for online APIs.

## Global Constraints

- PoB calculation logic remains authoritative; the model must not invent numeric results.
- API keys are never stored in plaintext files or embedded in the executable.
- Model weights are excluded from Git and the standard application package.
- The application must work without an online provider when a local model is installed.
- Every external calculation answer must include a traceable source/tool result.

---

### Task 1: Repository boundaries and local configuration

**Files:**
- Create: `agent/README.md`
- Create: `agent/config/model-providers.example.json`
- Create: `agent/knowledge/README.md`
- Create: `local-models/.gitkeep`
- Modify: `.gitignore`

**Interfaces:**
- Produces the documented directories and configuration contract used by later tasks.

- [ ] **Step 1: Add the directory documentation and provider configuration example.**
- [ ] **Step 2: Ignore model weights, local credentials, caches, and generated indexes.**
- [ ] **Step 3: Verify `git status --short` contains no ignored model artifacts.**
- [ ] **Step 4: Commit `chore: define agent repository boundaries`.**

### Task 2: PoB bridge and structured fact protocol

**Files:**
- Create: `src/Modules/AgentBridge.lua`
- Create: `src/Modules/AgentTrace.lua`
- Create: `agent/protocol/fact-schema.json`
- Test: `tests/agent/protocol/fact-schema.test.json`

**Interfaces:**
- Produces JSON facts with `buildId`, `queryScope`, `facts`, `sources`, and `calculationVersion`.
- Consumes existing PoB calculation state without duplicating calculation formulas.

- [ ] **Step 1: Define a schema for numeric facts and calculation sources.**
- [ ] **Step 2: Add a Lua bridge that returns only explicitly requested facts.**
- [ ] **Step 3: Add trace records for modifiers and ordering-sensitive effects.**
- [ ] **Step 4: Validate representative projectile and curse examples.**
- [ ] **Step 5: Commit `feat: expose PoB facts to agent runtime`.**

### Task 3: Agent runtime, tools, and RAG adapters

**Files:**
- Create: `agent/app/agent_loop.*`
- Create: `agent/tools/pob_tools.*`
- Create: `agent/knowledge/retriever.*`
- Create: `agent/prompts/system.md`
- Create: `agent/tests/tool_contracts.*`

**Interfaces:**
- Tool contract: `execute(name: string, arguments: object) -> {data: object, sources: array}`.
- Runtime contract: `answer(question: string, context: object) -> {text: string, toolCalls: array, sources: array}`.

- [ ] **Step 1: Define tool schemas for projectile count, curse limit, socket order, and damage explanation.**
- [ ] **Step 2: Route tool calls through the PoB bridge and reject unsupported mutations.**
- [ ] **Step 3: Retrieve relevant knowledge entries from local files/indexes.**
- [ ] **Step 4: Enforce a prompt rule that numeric claims require tool evidence.**
- [ ] **Step 5: Add contract tests for valid, missing, and contradictory facts.**
- [ ] **Step 6: Commit `feat: add PoB agent tools and retrieval contracts`.**

### Task 4: Online provider and secure API-key storage

**Files:**
- Create: `agent/providers/online_provider.*`
- Create: `agent/security/windows_credentials.*`
- Create: `agent/app/provider_router.*`
- Test: `agent/tests/provider_router.*`

**Interfaces:**
- `storeApiKey(provider: string, key: string) -> void`.
- `deleteApiKey(provider: string) -> void`.
- `generate(request: ModelRequest) -> ModelResponse`.

- [ ] **Step 1: Store and retrieve provider keys through Windows Credential Manager or DPAPI.**
- [ ] **Step 2: Add provider selection and explicit rate-limit/error handling.**
- [ ] **Step 3: Ensure keys never enter logs, prompts, crash reports, or PoB Lua state.**
- [ ] **Step 4: Test save, read, replace, delete, and unavailable-provider behavior.**
- [ ] **Step 5: Commit `feat: add secure online provider routing`.**

### Task 5: Optional local model manager

**Files:**
- Create: `agent/models/model_manifest.json`
- Create: `agent/models/model_manager.*`
- Create: `agent/providers/local_provider.*`
- Create: `packaging/model-download-policy.md`
- Test: `agent/tests/model_manager.*`

**Interfaces:**
- `listModels() -> ModelDescriptor[]`.
- `download(modelId: string, destination: path) -> DownloadResult`.
- `verify(modelId: string) -> VerificationResult`.
- `load(modelId: string) -> LocalModelHandle`.

- [ ] **Step 1: Define a manifest containing model URL, size, version, runtime, and SHA-256.**
- [ ] **Step 2: Implement resumable download and disk-space checks.**
- [ ] **Step 3: Verify the checksum before making a model selectable.**
- [ ] **Step 4: Route local inference through the same `ModelRequest` interface as online inference.**
- [ ] **Step 5: Add tests for incomplete, corrupt, and valid model files.**
- [ ] **Step 6: Commit `feat: add optional local model management`.**

### Task 6: PoB UI, packaging, and end-to-end verification

**Files:**
- Create: `src/Classes/AgentPanel.lua`
- Create: `packaging/agent-runtime-manifest.json`
- Create: `tests/agent/e2e-scenarios.md`
- Modify: existing PoB UI entry point identified during implementation

- [ ] **Step 1: Add the Agent button and chat panel without blocking PoB calculation.**
- [ ] **Step 2: Add provider/API-key and model-download settings.**
- [ ] **Step 3: Verify offline local-model mode and online API mode.**
- [ ] **Step 4: Run representative Impending Doom/Vixen's Entrapment scenarios and compare traces to PoB values.**
- [ ] **Step 5: Commit `feat: integrate agent panel and packaging`.**
