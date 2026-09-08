# Mechanism Tools

Mechanism Tools explain relationships already represented by PoB state. They expose facts and provenance; they do not claim a combat simulation when PoB has not calculated one.

## Socket and skill mechanics

- `get_socket_order`: returns original PoB gem order, enabled state, source/slot, link count, skill name, and active index.
- `get_support_links`: returns support gems attached to the resolved skill, including item-granted skill groups.
- `get_skill_chain`: returns `Chain`, `ChainMax`, `ChainRemaining`, and related string output from the selected active skill.
- `get_trigger_sequence`: returns PoB trigger metadata.
- `get_curse_application_order`: returns socket order and `not_simulated` when timing cannot be proven.

## Numeric mechanics

- `get_projectile_count` and `get_projectile_behavior` read PoB projectile output and attach modifier/breakdown evidence.
- `get_duration` reads the appropriate Duration output or Trauma calculation and includes gem level/quality and modifier sources.
- `get_conversion_chain` reads the skill conversion table.
- `get_effective_resistance` returns PoB effective multipliers, not reconstructed raw resistance.
- `get_elemental_penetration` reads per-element calculated penetration.
- `get_ailment_effect` exposes available calculated ailment/chance outputs.

## Status handling

An unavailable optional field is omitted inside `facts` and explained in `uncertainty`. A mechanism that would require a new simulator is `status: not_simulated`; it must not be described as calculated.
