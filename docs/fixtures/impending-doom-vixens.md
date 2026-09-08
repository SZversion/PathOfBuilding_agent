---
Status: Planned/Template
Authority: Supporting fixture design, not an executed fixture
---

# Impending Doom and Vixen's Entrapment Fixture Template

Purpose: verify item-granted/variant skill resolution, socket order, curse context, and explicit simulation limits.

```yaml
buildFile: "PoB code imported into a fixture build"
buildId: "impending-doom-vixens"
skillSet: "the selected curse setup"
mainSkill: "Impending Doom or item-granted skill context"
config: "curse and enemy settings from PoB"
enemyState: "curse limit and enemy conditions"
gamePatch: not_applicable
pobVersion: not_applicable
expectedOutputPath: "calcs.mainEnv.player.activeSkillList[skillIndex].output"
expectedBreakdownPath: "skillsTab.socketGroupList/displayGemList plus available breakdown"
```

Assertions: the item-provided skill is resolved from PoB synthetic groups, same-group supports are preserved, socket order is returned, and application timing is `not_simulated` unless PoB evidence directly provides it. Curse limit and calculated damage use PoB output.
