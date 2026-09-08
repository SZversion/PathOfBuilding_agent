---
Status: Planned/Template
Authority: Supporting fixture design, not an executed fixture
---

# Item-Granted Skill Fixture Template

Purpose: verify an item-provided skill and its socketed supports.

```yaml
buildFile: "build containing an item-granted skill"
buildId: "item-granted-skill"
skillSet: "selected Skill Set"
mainSkill: "item-granted skill name"
config: "current PoB Config"
enemyState: "current PoB enemy state"
gamePatch: not_applicable
pobVersion: not_applicable
expectedOutputPath: "activeSkillList[skillIndex].output"
expectedBreakdownPath: "skillsTab.socketGroupList[group].displayGemList"
```

Use PoB `sourceItem`, `gem.fromItem`, and synthetic socket group data. Verify support gems from the same item group apply to the granted skill. Do not manually recreate item support semantics.
