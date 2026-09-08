# Static Strike Fixture

Purpose: verify duration output, gem level/quality, and actor-plus-skill modifier provenance.

```yaml
buildFile: "3.29/static strike.xml"
buildId: "static-strike-3.29"
skillSet: "Endgame"
mainSkill: "Static Strike of Gathering Lightning"
config: "Endgame config"
enemyState: "loaded from PoB config"
gamePatch: "3.29"
pobVersion: null
expectedOutputPath: "calcs.mainEnv.player.activeSkillList[skillIndex].output.Duration"
expectedBreakdownPath: "calcs.mainEnv.player.activeSkillList[skillIndex].breakdown.DurationMod"
```

Compare raw PoB duration, UI display, Tool return, and final display separately. Include gem level/quality and increased/more source edges. A headless fixture may be partial when UI-only state is unavailable; report that status rather than substituting a formula.
