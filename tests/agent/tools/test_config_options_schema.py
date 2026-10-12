from pathlib import Path


CONFIG_OPTIONS = Path(__file__).parents[3] / "src" / "Modules" / "ConfigOptions.lua"


def test_config_override_registry_matches_pob_config_options_source():
    source = CONFIG_OPTIONS.read_text(encoding="utf-8")
    assert '{ var = "enemyIsBoss", type = "list"' in source
    assert '{ var = "resistancePenalty", type = "list"' in source
    assert '{ var = "conditionStationary", type = "count"' in source
    for key in ("usePowerCharges", "useFrenzyCharges", "useEnduranceCharges"):
        assert f'{{ var = "{key}", type = "check"' in source
    for key in ("overridePowerCharges", "overrideFrenzyCharges", "overrideEnduranceCharges"):
        assert f'{{ var = "{key}", type = "count"' in source
