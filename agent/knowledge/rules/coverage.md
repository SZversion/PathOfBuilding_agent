# Path of Exile 1 Core Rule Coverage

This checklist tracks missing rules. Only Path of Exile 1 is in scope. Rules are added to versioned JSON files after verification.

## P0 — Required for PoB explanations

### Damage calculation

- [ ] `increased` versus `more/less`
- [ ] `added damage` versus `gain as extra`
- [ ] damage conversion order
- [ ] resistance reduction, Exposure, curses, and penetration
- [ ] modifier scope for Hits versus Damage over Time
- [ ] weapon, melee, projectile, spell, and area damage tags

Sources: [Damage](https://www.poewiki.net/wiki/Damage), [Resistance penetration](https://www.poewiki.net/wiki/Resistance_penetration)

### Skills and gems

- [ ] Attack, Spell, Warcry, Aura, and Curse tags
- [ ] Projectile, AoE, Duration, Channelling, and Trigger tags
- [ ] Totem, Trap, Mine, and Brand proxy behavior
- [ ] Triggered skills versus `use a skill` conditions
- [ ] support gem link scope

Sources: [Skill](https://www.poewiki.net/wiki/Skill), [Gem tag](https://www.poewiki.net/wiki/Gem_tag)

### Defenses and survival

- [ ] Armour, Evasion, Energy Shield, and Ward
- [ ] Block, Spell Suppression, and Dodge scope
- [ ] Accuracy versus Evasion
- [ ] resistance caps and effective resistance
- [ ] mitigation versus avoidance

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
- [ ] Life, Mana, and Energy Shield recovery, regeneration, leech, and Recoup
- [ ] Reservation, Cost, and Reservation Efficiency
- [ ] Power, Frenzy, and Endurance Charges
- [ ] Projectile count, Pierce, Chain, Fork, and Split
- [ ] single-target overlap and shotgun behavior
- [ ] Buff, Debuff, Aura, Stance, and Guard Skill rules

## P2 — Later coverage

- [ ] Attributes and requirements
- [ ] Level, Experience, Ascendancy, and campaign rewards
- [ ] Map and monster modifiers
- [ ] Minion, Totem, Trap, and Mine ownership rules
- [ ] league-specific mechanics

## Collection principle

Use PoE Wiki for concepts and cross-references, then compare current values and behavior against PoB data and official patch notes. Store only the rules needed by the agent instead of copying entire wiki pages.

