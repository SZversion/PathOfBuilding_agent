# Snapshot and Diff Synchronization

## Normalized snapshot

The first request sends a normalized snapshot containing:

- canonical build ID, snapshot ID, and monotonic `revision`
- game patch, PoB version, and knowledge data revision when applicable
- Skill Set, Main Skill, Config, enabled state, and enemy state
- items, sockets, gems with level/quality/variant metadata
- passive allocation and cluster-jewel effects
- requested calculated outputs and Evidence Graph references

The raw XML is not sent to the external server.

The live `pob_agent` snapshot includes the currently selected Tree Spec, Skill Set,
Item Set, Config Set, main skill, enabled gems, Config values, and ordered set
catalogs together with PoB's calculated outputs. Unmentioned request fields use
these active selections. Explicit user mentions take priority for that request;
set IDs are resolved from the supplied catalogs, and temporary calculation
overrides are restored after the Tool call. Missing or ambiguous requested
targets require clarification. A planner clarification contradicted by supplied
live context is retried within the existing bounded planner repair budget.

## Diff

Later requests send `{baseRevision, revision, changes}`. Changes are limited to normalized item, skill, passive, Config, enabled-state, or selected-context fields. The Bridge recaptures the current PoB state before every request so direct user edits are included.

If the diff cannot be trusted, the Bridge sends a complete current snapshot instead. Correctness is preferred over a small payload.

## Revision protocol

1. Capture current state and assign a revision.
2. Send full snapshot for the first request or a diff from the last acknowledged revision.
3. Execute only a plan whose expected revision still matches.
4. After Tool execution or user UI changes, recapture and increment revision.
5. Discard stale Agent mutations when the revision differs.

The external server does not become the source of truth; its conversation context is advisory and is reconciled against the latest local snapshot.
