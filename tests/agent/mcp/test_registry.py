import pathlib
import json
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.mcp.registry import ToolContractError, tool_definitions, validate_tool_call
from agent.orchestration.agent_loop import ALLOWED_TOOLS
from agent.tool_catalog import TOOL_CATALOG, TOOL_GROUPS


def test_registry_matches_all_agent_loop_tools_and_has_unique_schemas():
    definitions = tool_definitions()

    assert len(definitions) == 32
    assert len({item["name"] for item in definitions}) == len(definitions)
    assert {item["name"] for item in definitions} == set(ALLOWED_TOOLS)
    assert all(item["description"].strip() for item in definitions)
    assert all(item["inputSchema"]["type"] == "object" for item in definitions)


def test_agent_loop_and_mcp_contracts_are_derived_from_one_catalog():
    definitions = {item["name"]: item for item in tool_definitions()}

    assert set(TOOL_CATALOG) == set(ALLOWED_TOOLS)
    assert set(definitions) == set(TOOL_CATALOG)
    assert all(spec.group in TOOL_GROUPS for spec in TOOL_CATALOG.values())
    for name, spec in TOOL_CATALOG.items():
        assert definitions[name]["description"] == spec.description
        assert definitions[name]["inputSchema"] == spec.input_schema


def test_registry_declares_required_arguments_and_search_constraints():
    definitions = {item["name"]: item for item in tool_definitions()}

    assert definitions["search_external"]["inputSchema"]["required"] == ["query"]
    assert definitions["search_external"]["inputSchema"]["properties"]["source"]["enum"] == ["poedb", "poewiki", "both"]
    assert definitions["search_external"]["inputSchema"]["properties"]["limit"]["maximum"] == 3
    assert set(definitions["compare_build_states"]["inputSchema"]["required"]) == {"beforeState", "afterState", "skillIndex"}


def test_validate_tool_call_normalizes_skill_shorthand():
    normalized = validate_tool_call("get_skill_dps", {"skill": "Flicker Strike"})

    assert normalized == {"skillName": "Flicker Strike"}


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("not_a_tool", {}),
        ("search_external", {}),
        ("search_external", {"query": "Arc", "limit": True}),
        ("search_external", {"query": "x" * 201}),
        ("get_skill_dps", {"skillIndex": "1"}),
        ("get_skill_dps", {"skillIndex": 0}),
        ("compare_build_states", {"beforeState": {}, "afterState": {}, "skillIndex": 1, "comparisonFields": [1]}),
        ("get_skill_dps", {"rawXml": "<build/>"}),
        ("get_character_stats", {"supportName": "Added Fire Damage"}),
    ],
)
def test_validate_tool_call_rejects_invalid_names_or_arguments(name, arguments):
    with pytest.raises(ToolContractError):
        validate_tool_call(name, arguments)


def test_mutation_tools_are_schema_validated_even_though_live_execution_is_gated():
    arguments = {
        "slot": "Weapon 1",
        "itemIdentity": "rare-sword",
        "itemText": "Rarity: Rare\nTest Sword",
        "expectedSnapshotRevision": "rev-1",
        "idempotencyKey": "request-1",
        "fingerprint": "item-fingerprint",
    }

    assert validate_tool_call("replace_item", arguments) == arguments


def test_every_tool_has_a_complete_machine_readable_design_contract():
    categories = {"context_resolution", "state_metadata", "calculation", "trace_evidence",
                 "comparison_simulation", "mutation", "knowledge_search"}
    for name, spec in TOOL_CATALOG.items():
        assert spec.category in categories
        assert spec.group in TOOL_GROUPS
        assert spec.purpose and spec.when_to_use and spec.constraints and spec.returns
        assert spec.timeout_seconds > 0
        assert spec.retry_policy in {"never", "transient_read_only"}
        assert spec.side_effect in {"read_only", "mutation_request"}
        assert isinstance(spec.idempotent, bool)
        assert spec.examples
        assert spec.error_codes
        assert spec.side_effect == "read_only" or spec.retry_policy == "never"
        for field in spec.input_schema["properties"].values():
            assert field.get("description", "").strip()
        example = json.loads(spec.examples[0])
        assert validate_tool_call(name, example["arguments"]) == example["arguments"]


def test_mcp_definitions_include_side_effect_annotations():
    definitions = {item["name"]: item for item in tool_definitions()}
    for name, spec in TOOL_CATALOG.items():
        annotations = definitions[name]["annotations"]
        assert annotations["readOnlyHint"] is (spec.side_effect == "read_only")
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is spec.idempotent
        assert annotations["openWorldHint"] is spec.open_world
