---
Status: Planned/Template
Authority: Supporting fixture design, not an executed fixture
---

# Variant Gem Fixture Template

Purpose: ensure a variant gem is not collapsed into its base gem name.

```yaml
buildFile: "build containing a variant gem"
buildId: "variant-gem-resolution"
skillSet: "selected Skill Set"
mainSkill: "variant granted-effect name"
config: "current PoB Config"
enemyState: "current PoB enemy state"
gamePatch: not_applicable
pobVersion: not_applicable
expectedOutputPath: "activeSkillList[skillIndex].activeEffect.grantedEffect and output"
expectedBreakdownPath: "activeSkillList[skillIndex].breakdown"
```

The resolver must retain granted-effect identity, base name, gem level, quality, and support links. Ambiguous base-name-only matches are rejected.
