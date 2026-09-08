# Skill Context and Resolver

The resolver follows PoB's calculated and synthetic structure rather than searching only visible gem text.

## Resolution sequence

1. Resolve Skill Set by exact title, case-insensitive title, or 1-based order.
2. Activate the target context temporarily and preserve the original active Skill Set, Main Skill, and calculation input.
3. Scan PoB's active calculated skills by granted-effect name and base name.
4. Return an error for missing or ambiguous exact matches.
5. Rebuild output, read the target output/breakdown, and restore the original context on both success and error.

## Synthetic socket groups

For saved builds, PoB-generated socket groups are authoritative. Resolver metadata may include:

- `sourceItem` or `gem.fromItem` → `item_granted`
- `sourceNode` → `tree_granted`
- generated group source → `generated`
- otherwise → `socketed`

Use `displayGemList` when available so item-granted skills include support gems from the same group; fall back to `gemList`. This handles item-provided skills, tree-granted skills, triggered skills, variant gems, and support order without rebuilding PoB linkage rules.

Unresolved or ambiguous contexts return `unavailable`/error evidence rather than guessing.
