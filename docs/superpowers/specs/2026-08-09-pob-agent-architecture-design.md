# PoB Agent Architecture Design

## Goal

Build a PoB-centered assistant that answers questions from authoritative PoB calculations and explanatory game knowledge, with online API access as the default and optional local-model execution for capable PCs.

## Decisions

- PoB remains the authoritative deterministic calculation engine.
- The Agent is a separate sidecar/runtime connected to PoB through a narrow JSON protocol.
- The model is replaceable: online provider by default, local Qwen-compatible runtime as an optional mode.
- User API keys are stored in Windows Credential Manager/DPAPI, never in plaintext configuration or Lua state.
- Model weights are downloaded through an in-app model manager and excluded from Git and the standard installer.
- RAG knowledge is local and versioned; numeric claims must cite PoB tool output.

## Runtime flow

```text
Question
  -> Agent intent/router
  -> PoB tools + local knowledge retrieval
  -> online provider OR local model
  -> answer with calculation trace and sources
```

## Repository layout

```text
src/                         # upstream PoB Lua application
  Classes/AgentPanel.lua     # Agent UI entry point
  Modules/AgentBridge.lua    # structured PoB facts
  Modules/AgentTrace.lua     # modifier/order trace
agent/                       # sidecar runtime
  app/                        # orchestration and provider routing
  tools/                      # PoB tool schemas and handlers
  knowledge/                  # source files and retriever
  prompts/                    # system and answer-format prompts
  providers/                  # online/local model adapters
  models/                     # manifests and model manager, not weights
  security/                   # Windows credential storage adapter
  protocol/                   # JSON schemas
tests/agent/                  # tool and end-to-end checks
packaging/                    # manifests, installer/download policy
local-models/                 # ignored user-downloaded weights
```

## Acceptance criteria

- A user can enter an API key without administrator privileges and use online mode.
- A user can download, verify, select, and remove a local model from the UI.
- Online and local modes consume the same `ModelRequest` interface.
- Answers for representative projectile, curse-limit, and socket-order questions show PoB-derived values and sources.
- No API key or model weight is committed to the repository or emitted in logs.
