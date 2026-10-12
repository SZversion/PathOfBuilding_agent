import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import extract_context_overrides
from agent.orchestration.runtime import SnapshotSync


def test_only_explicit_item_set_is_extracted():
    assert extract_context_overrides("2번 장비셋으로 DPS 알려줘") == {"activeItemSet": 2}


def test_unmentioned_context_is_preserved_and_override_is_provenanced():
    snapshot = SnapshotSync().prepare(
        {"activeItemSet": {"id": 1}, "activeSkillSet": {"id": 4}},
        {"activeItemSet": 2},
    )
    assert snapshot["snapshot"]["activeSkillSet"] == {"id": 4}
    assert snapshot["snapshot"]["contextProvenance"]["activeItemSet"]["provenance"] == "explicit_override"
