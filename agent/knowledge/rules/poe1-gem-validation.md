# PoE1 Gem Mechanics P0 Validation

Status: partial; this document is a fixture gate, not a claim that every gem rule is canonical.

## Fixture matrix

| Requirement | Fixture | Current result | Promotion gate |
|---|---|---|---|
| support-link/compatibility (2) | Static Strike of Gathering Lightning; second compatible/incompatible link | 0 paired fixtures | Two loaded PoB outputs and support enablement traces |
| variant/greater/awakened (2) | Vaal Arc of Oscillating; second variant support | 1 observed variant | Two distinct `variantId`/`grantedEffectId` observations |
| item-granted skill (2) | Impending Doom; item-provided second skill | planned | Synthetic socket group and source marker captured from PoB |
| trigger restriction (2) | Trigger support; second trigger/proxy | planned | Trigger markers, restrictions, cooldown and group captured |
| level/quality (2) | Arc (level 21/quality 20); Static Strike (level 20/quality 20) | 2 observed instances | Independent PoB output/breakdown comparison |

## Observed fixtures

### Arc of Oscillating

- File: `C:/Users/SZ/Documents/Path of Building/Builds/3.29/arc.xml`
- PoB ref: `1919296d052cb6934e810f763f9c34f50622a958`
- Skill Set: `1` (no title attribute observed)
- Main skill: `Vaal Arc of Oscillating`
- Config: `Default` (`id=1`)
- Gem identity: `gemId=Metadata/Items/Gems/SkillGemVaalArc`, `variantId=VaalArcAltY`, `skillId=VaalArc`
- Level/quality: `21/20`
- Supports observed: Greater Chain, Increased Critical Damage, Archmage, Greater Spell Echo, Arcane Surge
- Status: `fixture_verified` for identity and level/quality; not a complete support compatibility or variant rule proof.

### Static Strike of Gathering Lightning

- File: `C:/Users/SZ/Documents/Path of Building/Builds/3.29/static strike.xml`
- PoB ref: `1919296d052cb6934e810f763f9c34f50622a958`
- Skill Set: `7`, title `Midgame ` (XML observed)
- Main skill: `Static Strike of Gathering Lightning`
- Config: `Endgame` (`id=1` exists; active selection requires runtime verification)
- Gem identity: `gemId=Metadata/Items/Gems/SkillGemStaticStrike`, `variantId=StaticStrikeAltX`, `skillId=StaticStrikeAltX`
- Level/quality: `20/20`; Trauma support `21/20`
- Status: `partial`; exact active configuration and output fixture still need runtime capture.

## Validation rules

1. A Wiki search snippet is `temporary_evidence`; it cannot advance a rule past `source_checked`.
2. PoB source behavior may advance a rule to `pob_checked`, but not to `canonical` without a matching fixture.
3. Missing item-granted, trigger, alternate-quality, awakened/greater, or corrupted fixtures remain `planned` or `unverified`.
4. Live server timing is `not_simulated` even when PoB models a tick schedule.
5. Conflicting source claims are stored as `conflict`; they are not averaged or silently merged.

## RAG mapping

RAG chunks are one claim per rule ID. Index only after recording `status`, `uncertainty`, source metadata, PoB evidence, and fixture references. Planned/unverified/conflict records are retrievable for explanation of uncertainty but are excluded from authoritative final-value retrieval.
