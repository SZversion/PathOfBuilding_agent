---
Status: Planned/Template
Authority: Supporting fixture design, not an executed fixture
---

# Build Comparison Fixture Template

Purpose: compare the current build with a second build imported from a PoB code.

```yaml
buildA:
  buildFile: null
  buildId: null
  skillSet: null
  mainSkill: null
  config: null
  enemyState: null
  gamePatch: not_applicable
  pobVersion: not_applicable
  expectedOutputPath: null
  expectedBreakdownPath: null
buildB:
  buildFile: null
  buildId: null
  skillSet: null
  mainSkill: null
  config: null
  enemyState: null
  gamePatch: not_applicable
  pobVersion: not_applicable
  expectedOutputPath: null
  expectedBreakdownPath: null
```

When instantiated, the comparison uses already-calculated outputs and reports before/after/delta plus source edges. Each build records its own versions; different major versions reject comparison and minor mismatch is warned. The second build is imported by PoB code, not a user-selected XML file.
