# Path of Exile 1 Core Rule Coverage

This checklist tracks missing rules. Only Path of Exile 1 is in scope. Rules are added to versioned JSON files after verification.

Current status: P0 has an initial PoB comparison; unresolved items remain explicitly marked in `validation-report.md` and `poe1-pob-validation.json`.

## P0 — Required for PoB explanations

### Damage calculation

- [x] `increased` versus `more/less` (operation verified; universal order partial)
- [x] `added damage` versus `gain as extra` (gain-as-extra verified; added damage partial)
- [x] damage conversion order
- [x] resistance reduction, Exposure, curses, and penetration (ordering partial)
- [x] modifier scope for Hits versus Damage over Time
- [x] weapon, melee, projectile, spell, and area damage tags

Sources: [Damage](https://www.poewiki.net/wiki/Damage), [Resistance penetration](https://www.poewiki.net/wiki/Resistance_penetration)

### Skills and gems

- [x] Attack, Spell, Warcry, Aura, and Curse tags (tag data verified)
- [x] Projectile, AoE, Duration, Channelling, and Trigger tags (tag data verified)
- [ ] Totem, Trap, Mine, and Brand proxy behavior
- [ ] Triggered skills versus `use a skill` conditions
- [ ] support gem link scope

Sources: [Skill](https://www.poewiki.net/wiki/Skill), [Gem tag](https://www.poewiki.net/wiki/Gem_tag)

### Defenses and survival

- [x] Armour, Evasion, Energy Shield, and Ward
- [x] Block, Spell Suppression, and Dodge scope
- [x] Accuracy versus Evasion
- [x] resistance caps and effective resistance
- [x] mitigation versus avoidance

Sources: [Defences](https://www.poewiki.net/wiki/Defences), [Evasion](https://www.poewiki.net/wiki/Evasion), [Spell suppression](https://www.poewiki.net/wiki/Spell_suppression)

### Curses and ailments

- [ ] Hex versus Mark
- [ ] curse limits and curse application order
- [ ] Ignite, Bleed, and Poison application and DoT rules
- [ ] Chill, Freeze, Shock, Scorch, Brittle, and Sap effects
- [ ] ailment effect versus ailment damage modifiers

Sources: [Ailment](https://www.poewiki.net/wiki/Ailment), [Curse](https://www.poewiki.net/wiki/Curse)

## P1 — Frequently used extensions

- [ ] Critical Strike Chance, Multiplier, Lucky, and Unlucky
- [ ] Accuracy and critical strike re-roll behavior
- [x] Life, Mana, and Energy Shield recovery, regeneration, and leech (Recoup pending)
- [x] Reservation, Cost, and Reservation Efficiency
- [x] Power, Frenzy, and Endurance Charges
- [ ] Projectile count, Pierce, Chain, Fork, and Split
- [ ] single-target overlap and shotgun behavior
- [x] Buff, Debuff, Aura, Stance, and Guard Skill rules (core state paths verified; full interaction matrix pending)

## P2 — Later coverage

- [x] Attributes and requirements (attribute-derived stats verified; all requirements pending)
- [x] Level, Experience, Ascendancy, and campaign rewards (level-based resources verified; experience/rewards pending)
- [x] Map and monster modifiers (enemy-level scaling verified; full modifier matrix pending)
- [ ] Minion, Totem, Trap, and Mine ownership rules
- [ ] league-specific mechanics

## Collection principle

Use PoE Wiki for concepts and cross-references, then compare current values and behavior against PoB data and official patch notes. Store only the rules needed by the agent instead of copying entire wiki pages.
