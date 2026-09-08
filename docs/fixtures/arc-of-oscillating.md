---
Status: Smoke/Observed
Authority: Local fixture observation; expected values remain PoB-authoritative
---

# Arc of Oscillating Fixture

Purpose: verify variant-skill resolution, chain facts, cast speed, and source trace.

```yaml
buildFile: "C:/Users/SZ/Documents/Path of Building/Builds/3.29/arc.xml"
buildId: "arc-3.29"
skillSet: "SkillSet id=1; activeSkillSet=1; no title attribute in XML"
mainSkill: "Vaal Arc of Oscillating (Skill mainActiveSkill=2; Calcs skill_number=1)"
config: "ConfigSet id=1, title=Default, activeConfigSet=1"
enemyState: "Default Config placeholders from XML, including enemy level 84, resistances 50, armour 61989, and projectileDistance 40"
gamePatch: "3.29 (build path and Tree treeVersion=3_29; XML targetVersion=3_0 is preserved as observed metadata)"
pobVersion: "1919296d052cb6934e810f763f9c34f50622a958"
dataRevision: null
expectedOutputPath: "calcs.mainEnv.player.activeSkillList[1].output.{ChainMax,Speed,Time}"
expectedBreakdownPath: "calcs.mainEnv.player.activeSkillList[1].breakdown plus AgentTrace modifier sources"
```

Assertions: exact variant name resolves, PoB output is used as-is, chain and cast-speed sources are represented, and the original active context is restored after temporary resolution. Run with LuaJIT as a smoke/integration test.
