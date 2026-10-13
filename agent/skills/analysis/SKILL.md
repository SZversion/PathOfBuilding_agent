---
name: analysis
description: Use to explain current calculated values, applied effects, and game mechanics, or evaluate ways to achieve an explicitly requested numerical target while considering tradeoffs. Select compare as well when evaluating changes or differences between states.
---

# Analysis, mechanisms, and requested targets

## Determine what needs explaining

Use the user's explicit skill, stat, effect, or target; otherwise resolve the subject from the current active selections and supplied snapshot. Reuse available skill/gem metadata, conditions, and outputs before requesting more evidence.
A question about why the current DPS has a particular value asks for calculation analysis. Claims such as high or low need a reference; do not invent one. A question about why DPS differs from another build requires the comparison skill and evidence from both states.
A question about reaching a specific target, such as a 4.8 m skill radius, requests possible methods and their consequences. Evaluate alternatives only within that explicitly requested goal. Do not introduce unsolicited optimization or replacement recommendations for a question that only asks for an explanation.
If necessary information is absent, first use available Tools to obtain it. Ask only for required information that no available Tool can retrieve. Tool failures are execution errors; missing calculation evidence is an explanation limitation, not proof that the user omitted information.

## Obtain calculation and mechanism evidence

Use Tool purposes and input schemas to select the evidence needed for the requested question. Use explain_stat for a specific stat's modifier trace, with the exact PoB output key and skillName or skillIndex when skill-specific. Use get_damage_breakdown, get_skill_breakdown, or resolve_skill_context where their contracts match the question. Use the relevant dedicated Tool for triggers, conversion, penetration, resistance, chains, projectiles, duration, curses, or other supported mechanisms.
Read current values, intermediate calculation values, modifier sources, enabled states, and conditional effects. Do not assume that an item or gem effect is active merely because its text exists; check actual applicability and PoB evidence.
PoB output is authoritative for current-build numbers. Local knowledge and permitted external search can explain general rules when necessary; distinguish those rules from evidence of what this build actually applies. Do not substitute an independently estimated calculation for a missing PoB result.

## Explain the current result

Present the requested result and units, the relevant active conditions, the contributors and supported calculation sequence, and their sources. Include only intermediate values necessary to explain the question. State where effects apply and which relevant conditions disable them.
For a question such as why current skill DPS is a particular value, connect the applicable base damage, scaling, speed, critical strikes, supports, and enemy conditions only where calculation evidence supports those contributors. For radius or area, distinguish radius, area, units, and displayed rounding; never equate a percentage increase in area with the same percentage increase in radius.
Clearly separate confirmed calculations, general game rules, inference, and unavailable evidence. Do not claim an exact contribution for an effect without evidence supporting it. Stop when the requested result or mechanism is explained.

## Evaluate an explicitly requested target

Establish the target metric and units, the current baseline, and any user-specified constraints. For a 4.8 m target, confirm the relevant skill's radius and whether the available unrounded or displayed result actually satisfies the threshold; state uncertainty if precision cannot establish it.
Identify candidates from the supplied build, supported effects, and available knowledge. Preserve named skills and conditions unless the user requests changing them. Do not invent candidate items, effect values, compatibility, or attainable results.
When assessing changed states, use the compare skill and supported PoB calculation/comparison Tools. A target-achievement question may require both analysis and compare skills. Do not claim that a candidate has been tested or applied without a corresponding Tool result. The current planner cannot execute mutation Tools; if a candidate cannot be simulated through the available read-only comparison capabilities, label it unverified and explain what evidence is missing.
Evaluate the target result alongside relevant DPS, defensive values, resource costs and reservation, and other consequences of the proposed change. Include gear/passive/gem requirements, displaced effects, and investment or availability constraints when evidence is available. Do not invent market prices or costs.
Meeting the target alone does not establish a useful solution. For example, a candidate that reaches the radius but halves DPS must disclose that loss and be considered alongside alternatives. Do not silently choose an acceptable loss threshold or a weighting between damage, defence, resources, and investment.
Honor explicit user constraints. When no tradeoff limits are specified, present verified candidates with their target values, benefits, losses, requirements, and uncertainties side by side, leaving the tradeoff visible. Do not ask for a preference merely to avoid presenting the supported alternatives.
Explain which evaluated candidates satisfy the target and constraints, and why one may be preferable under a stated priority. Limit conclusions to the candidates and effects actually evaluated; do not claim a globally optimal solution or that no solution exists because a bounded search failed.
If none of the evaluated candidates satisfies the target and supplied constraints, say so and identify the remaining limitation. Finish with supported results and tradeoffs; a method recommendation does not authorize applying it or saving the build.
