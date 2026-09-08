# RAG Index Update Candidates

This list records chunks that should be added or refreshed in the local RAG index. It is not itself canonical evidence.

## Required P0 chunks

- `modifier.increased_decreased`
- `modifier.more_less`
- `damage.base_effectiveness_added`
- `damage.gain_conversion`
- `damage.resistance_penetration`
- `projectile.chain_behavior`
- `curse.ailment.interaction`
- `skill_support.item_granted_variant`
- `resource.duration.context`

## Gem mechanics P0 chunks

- `gem.identity.variant`
- `gem.level.quality`
- `gem.tags.skill_flags`
- `support.compatibility`
- `gem.item_granted.source`
- `gem.synthetic_socket_group`
- `gem.trigger.compatibility`
- `gem.trigger.cooldown_tick`
- `gem.alternate_quality`
- `gem.exceptional_awakened_greater`
- `gem.corrupted`

Each chunk must be one claim per rule ID and include `scope`, `gamePatch`, `pobVersion`, `dataRevision`, `status`, `uncertainty`, `sources`, and the relevant `pobEvidence` or fixture reference. Chunks with `planned`, `partial`, `unverified`, or `conflict` status must be filtered from authoritative final-value retrieval.

## Source and retrieval filters

- Prefer PoB output/breakdown for current calculated values.
- Prefer official patch/game data, then matching PoB code, then PoE Wiki/PoEDB for game rules.
- Keep external search as `temporary_evidence`; do not index it as canonical without review and fixtures.
- Preserve source URL, wikiOldid, retrievedAt, wikiLastModified, license, attribution, repository ref/commit, and patch applicability.
- Gem chunks use `agent/knowledge/sources/poe1-gem-p0-inventory.json` and `agent/knowledge/rules/poe1-gem-mechanics-p0.json`; filter by PoE edition, patch applicability, verification state, and uncertainty.

## Domain rule files awaiting index review

`modifier.json`, `skill.json`, `skill-gem.json`, `item-socket.json`, `attack.json`, `spell.json`, `curse.json`, `warcry.json`, `aura.json`, `minion.json`, `totem.json`, and `trap.json` are claim-oriented inputs. Create one chunk per rule ID, retain relatedRuleIds/dependencies/sourceEdges, and exclude planned/unverified/conflict records from authoritative retrieval.

## Build and equipment domain chunks

The nine domain files `passive-skill.json`, `ascendancy-class.json`, `attribute.json`, `stat.json`, `quest-rewards.json`, `weapon.json`, `unique-item.json`, `armour-equipment.json`, and `jewellery.json` are indexed by rule ID only after source and fixture review. Inventory pages and impact edges are in `agent/knowledge/sources/poe1-build-domain-manifest.json`. Current values must be retrieved from PoB output; do not embed current character values in RAG.
