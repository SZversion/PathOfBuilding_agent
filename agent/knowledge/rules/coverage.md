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

#### Gem mechanics P0 (2026-09-08)

- [x] gem identity fields and variant separation (PoB checked; fixture promotion pending)
- [x] gem level and quality fields (two observed build instances)
- [x] gem tags versus resolved skill flags (PoB checked)
- [ ] support compatibility and item-granted exceptions (fixture pair missing)
- [ ] synthetic socket groups for item-provided skills (runtime capture missing)
- [ ] trigger compatibility and restrictions (fixture pair missing)
- [ ] trigger cooldown/tick model (PoB checked; live server timing not simulated)
- [ ] alternate quality, exceptional/awakened/greater, and corrupted states (planned)

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
- [x] Life, Mana, and Energy Shield recovery, regeneration, leech, and Recoup
- [x] Reservation, Cost, and Reservation Efficiency
- [x] Power, Frenzy, and Endurance Charges
- [x] Projectile count, Pierce, Chain, Fork, and Split (count and scope verified; secondary behaviors pending)
- [x] single-target overlap and shotgun behavior (requires skill fixtures)
- [x] Buff, Debuff, Aura, Stance, and Guard Skill rules (core state paths verified; full interaction matrix pending)

## P2 — Later coverage

- [x] Attributes and requirements (attribute-derived stats verified; all requirements pending)
- [x] Level, Experience, Ascendancy, and campaign rewards (experience and Ascendancy paths verified; full quest catalog pending)
- [x] Map and monster modifiers (enemy-level scaling verified; full modifier matrix pending)
- [ ] Minion, Totem, Trap, and Mine ownership rules
- [ ] league-specific mechanics

## Collection principle

Use PoE Wiki for concepts and cross-references, then compare current values and behavior against PoB data and official patch notes. Store only the rules needed by the agent instead of copying entire wiki pages.

## 2026-09-08 seed collection status

The manual Wiki seed and link inventory is stored in:

- `agent/knowledge/sources/poe1-wiki-manifest.json`
- `agent/knowledge/sources/poe1-p0-inventory.json`
- `agent/knowledge/rules/poe1-p0-planned.json`

The seed pages `Game mechanics` and `Keyword` were discovered with stable oldids, but direct page fetches returned HTTP 403 in the collection run. They are therefore navigation overviews, not canonical rule evidence. Link targets are tracked as discovered/unfetched until parsed and verified.

No P0 domain has been promoted to canonical solely from this seed. The P0 minimum fixture counts are recorded in the inventory; missing fixtures keep items planned or unverified. P1 and P2 links remain inventory-only for MVP.

## Domain rule-file inventory (2026-09-08)

- [x] modifier runtime operation shell (`modifier.json`)
- [x] skill and socketed gem identity shells (`skill.json`, `skill-gem.json`)
- [x] item socket/link shell (`item-socket.json`)
- [x] attack and spell search domains (`attack.json`, `spell.json`)
- [x] curse interaction shell (`curse.json`)
- [ ] warcry, aura, minion, totem, and trap P1 fixtures (`planned`)

## Build and equipment domain inventory (2026-09-08)

- [ ] passive allocation and source trace (`passive-skill.json`)
- [ ] ascendancy allocation and class restrictions (`ascendancy-class.json`)
- [ ] attribute versus derived stat separation (`attribute.json`, `stat.json`)
- [ ] quest reward act/class/patch index (`quest-rewards.json`, P1)
- [ ] weapon local/global and hand comparison (`weapon.json`)
- [ ] unique override/granted interaction (`unique-item.json`)
- [ ] armour defence comparison (`armour-equipment.json`)
- [ ] ring/amulet/belt comparison (`jewellery.json`)

All nine are currently planned because the required representative fixtures have not been captured.
