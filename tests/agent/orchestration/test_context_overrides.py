import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import extract_context_overrides
from agent.orchestration.agent_loop import resolve_active_context
from agent.orchestration.runtime import SnapshotSync


def test_only_explicit_item_set_is_extracted():
    assert extract_context_overrides("2번 장비셋으로 DPS 알려줘") == {"activeItemSet": 2}


def test_unmentioned_context_is_preserved_and_override_is_provenanced():
    snapshot = SnapshotSync().prepare(
        {"activeItemSet": {"id": 1}, "activeSkillSet": {"id": 4}},
        {"activeItemSet": 2},
    )
    assert snapshot["snapshot"]["activeSkillSet"] == {"id": "4"}
    assert snapshot["snapshot"]["contextProvenance"]["activeItemSet"]["provenance"] == "explicit_override"


def test_context_selection_normalizes_numeric_and_string_ids():
    context = {"activeSkillSet": {"id": "9"}, "skillSets": [{"id": 2}, {"id": 9}],
               "activeItemSet": {"id": 3}, "itemSets": [{"id": 3}],
               "activeSpec": {"id": 1}, "activeConfigSet": {"id": 8}}
    selection = resolve_active_context(context)["selected"]
    assert {key: value["id"] for key, value in selection.items()} == {
        "skillSet": "9", "itemSet": "3", "treeSpec": "1", "configSet": "8"}
    assert resolve_active_context(context, text="1번 스킬셋 DPS")["selected"]["skillSet"]["id"] == "2"
