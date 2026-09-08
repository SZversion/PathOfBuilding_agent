# Integration Fixtures

Fixture status is explicit. `Status: Verified` or `Status: Smoke` means a real build path and observed PoB context are recorded. `Status: Planned/Template` means the document is a design template and must not be presented as an existing fixture.

For an existing fixture, `gamePatch` and `pobVersion` should be concrete when observed. Use `null` only when the fixture exists but the applicable value could not be observed. Use `not_applicable` for a planned/template document that has no real fixture or version context.

Fixtures validate the Bridge against real or controlled PoB states. Each fixture records build file/id, Skill Set, Main Skill, Config, enemy state, game patch, PoB version, expected output path, and expected breakdown path. Version metadata is `null`/`not_applicable` only when it genuinely does not apply.

Run Lua integration fixtures with the configured LuaJIT. A fixture may be a smoke test when exact patch-sensitive values are not stable, but it must report `calculated`, `unavailable`, `not_simulated`, or `conflict` explicitly.

- [arc-of-oscillating.md](arc-of-oscillating.md)
- [static-strike.md](static-strike.md)
- [impending-doom-vixens.md](impending-doom-vixens.md)
- [variant-gem.md](variant-gem.md)
- [item-granted-skill.md](item-granted-skill.md)
- [build-comparison.md](build-comparison.md)
