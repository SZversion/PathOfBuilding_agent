---
name: lookup
description: Use for connection status, active build or set selection, skill and item information from supplied context or requested DB/Wiki sources, current calculated values, and finding the highest-DPS skill. Excludes requested changes, comparisons, and modifier or mechanism explanations.
---

# Status, lookup, and values

Use the supplied snapshot for active build, tree/spec, Skill Set, Item Set, Config, Main Skill, socket groups, and gem names, levels, qualities, and enabled state. Only query values or evidence absent from the supplied input.
Start by checking whether the requested value is already available for the requested target and current calculation conditions. For the supplied main skill, calculatedSnapshot.outputs contains its current calculated values. If mainSkill.name matches Arc of Oscillating and outputs.CastRate is present, answer using that cast rate; return steps=[] instead of searching or querying it again. Apply the same rule to other supplied values and matching targets.
lookup is the name of these instructions, not a game skill or search subject. Do not search for "lookup skill Path of Exile". External game pages cannot establish the current build's calculated values.
Decide whether supplied information answers the question before selecting any lookup or search Tool. Distinguish a current-build value from a request for a skill or item's game data in PoEDB or PoE Wiki. An explicit request to consult a DB or Wiki may require that source even when the build contains the subject's name; it does not authorize unrelated searches.

For DB/Wiki lookup, first identify the specific skill or item named by the user, resolving its name from supplied canonical names or aliases when available. Construct query from that subject's canonical name; add only a specific property or variant explicitly needed by the question. For a whole skill or item page, the subject name alone is enough.
Never turn every received argument or snapshot component into a search query. Do not search instruction names, schema field names, JSON fragments, set IDs, revisions, gem levels, or unrelated skills/items merely because they appear in the input. Do not enumerate the build's gems or equipment unless the user requested those subjects.
Set source=poedb for a requested DB lookup, source=poewiki for a requested Wiki lookup, or source=both for a needed lookup across both sources. source is a service selector, not a URL. One named subject normally needs one search; do not repeat that query with different sources or limits to fill the step budget. Use a valid limit from the Tool schema.
Examples of search arguments for explicitly requested sources:
```json
{"query":"Arc of Oscillating","source":"poedb","limit":1}
```
```json
{"query":"Mageblood","source":"poewiki","limit":1}
```
Choose the actual subject from the question; these examples do not authorize searching both subjects. Reuse a supplied matching DB/Wiki result instead of fetching it again. If the subject cannot be identified, resolve only that missing target through an applicable alias Tool or request clarification; never substitute a generic search such as "skill Path of Exile".
Connection status requires an actual connection result; a stored snapshot alone does not prove the current connection is healthy. Use supplied MCP connection/discovery results when available. Do not invent a connection-status tool.
Use get_highest_dps_skill for the highest-DPS skill across the active build only when the supplied context does not already provide a complete answer. This request needs no gem name, gem level, or preliminary alias-resolution calls.
Use get_character_stats for missing character-wide life, mana, attributes, and other supported character totals. For a specific missing skill value, select the canonical tool whose input schema and purpose match that value. A single missing-value lookup normally needs one call; do not query every skill or gem when the user asked about one target. The maximum step count is a ceiling, not a required number of calls.
Do not use explain_stat unless modifier evidence was requested. Do not change sets, Config, gems, items, or passives to perform a lookup. Do not invent aliases or arguments for canonical names already in the input.
If a required target is absent from the supplied context, first check the available Tool descriptions and schemas for a way to retrieve it. Use that Tool before considering a question; missing input alone is not a reason to ask. Ask the user only when no available Tool can retrieve the required target, and identify only the fields that cannot be retrieved. Otherwise keep ambiguities empty. A Tool failure is an execution error and must not be presented as the absence of a retrieval Tool.
Finish once the requested status or values have been obtained. Report relevant units and active calculation conditions; describe unavailable or partial values accurately.
