# Comparison and Mutation Tools

Comparison is performed by PoB before and after a requested in-memory change. The Agent does not estimate a delta from text.

## Sequence

1. Capture current state and revision.
2. Parse and normalize the requested item, gem, passive, or cluster-jewel change.
3. Verify target context and expected revision.
4. Apply the change to the current in-memory PoB build.
5. Let PoB recalculate.
6. Read output, breakdown, modifier sources, and mechanism facts.
7. Return before/after/delta facts and Evidence Graph.

The current UI changes immediately. PoB `Save` and `Save As` remain the only persistence actions.

## Comparison

`compare_build_states` compares numeric scalar keys from two already-calculated PoB outputs and returns `{before, after, delta}`. `compare_support_effect` and `explain_damage_change` preserve the changed support identity and the PoB-derived delta.

## Conflicts

If the user changes the UI while a plan is pending, the revision no longer matches. The Bridge discards the stale mutation, preserves the user's state, and requests a fresh plan. Missing outputs are `partial` or `unavailable`, never invented.
