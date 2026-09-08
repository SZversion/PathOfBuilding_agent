# Architecture Documentation

Authoritative product policy lives in `AGENT.md`, `CUSTOMER.md`, `PRD_SDD.md`, and the knowledge authoring documents. This directory explains the implementation shape that follows those policies.

- [bridge.md](bridge.md): PoB ↔ local Bridge ↔ external AI boundary
- [snapshot-sync.md](snapshot-sync.md): normalized snapshots, diffs, and revisions
- [cache-lifecycle.md](cache-lifecycle.md): build-scoped local cache and Save As behavior
- [agent-orchestration.md](agent-orchestration.md): plan, local execution, search, and answer flow

The Bridge is authoritative for PoB state and execution. The external AI server plans and explains; it never reads local files or executes local tools directly.
