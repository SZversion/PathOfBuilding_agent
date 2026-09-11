import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop, PLANNER_SYSTEM, validate_plan
from agent.orchestration.runtime import SnapshotSync, execute_plan
from agent.providers.openai_compatible import OpenAICompatibleClient


def test_plan_schema_allows_distinct_calls_but_rejects_mutation_and_exact_duplicate():
    plan = {"intent": "stat", "steps": [
        {"tool": "get_skill_stats", "arguments": {"skillName": "Arc"}},
        {"tool": "get_skill_stats", "arguments": {"skillName": "Fireball"}},
    ]}
    assert validate_plan(plan)["steps"][1]["arguments"]["skillName"] == "Fireball"
    with pytest.raises(ValueError):
        validate_plan({"steps": [{"tool": "get_skill_stats", "arguments": {"skillName": "Arc"}}, {"tool": "get_skill_stats", "arguments": {"skillName": "Arc"}}]})
    with pytest.raises(ValueError):
        validate_plan({"steps": [{"tool": "replace_item", "arguments": {}}]})


def test_plan_schema_validates_declared_types_and_revision():
    invalid_plans = [
        {"intent": 1, "steps": []},
        {"metadata": [], "steps": []},
        {"steps": [{"tool": 1, "arguments": {}}]},
        {"steps": [{"tool": "get_skill_stats", "arguments": [], "expectedSnapshotRevision": None}]},
        {"steps": [{"tool": "get_skill_stats", "arguments": {}, "expectedSnapshotRevision": 3}]},
    ]
    for invalid in invalid_plans:
        with pytest.raises(ValueError):
            validate_plan(invalid)


def test_planner_prompt_uses_canonical_read_only_catalog():
    assert "get_curse_limit" in PLANNER_SYSTEM
    assert "get_projectile_count" in PLANNER_SYSTEM
    assert "Check Curse Limit" not in PLANNER_SYSTEM
    assert "Never invent, translate, or paraphrase Tool names" in PLANNER_SYSTEM
    assert '"tool":"get_curse_limit"' in PLANNER_SYSTEM
    with pytest.raises(ValueError):
        validate_plan({"steps": [{"tool": "Check Curse Limit", "arguments": {}}]})


def test_revision_is_not_part_of_duplicate_identity():
    planned = {"steps": [
        {"tool": "get_skill_stats", "arguments": {"skillName": "Arc"}, "expectedSnapshotRevision": "rev-1"},
        {"tool": "get_skill_stats", "arguments": {"skillName": "Arc"}, "expectedSnapshotRevision": "rev-2"},
    ]}
    assert len(validate_plan(planned)["steps"]) == 2
    result = execute_plan("q", planned, handlers={"get_skill_stats": lambda args: {"evidenceGraph": {}}}, snapshot_revision_value="rev-1")
    assert result["steps"][0]["status"] == "ok"
    assert result["steps"][1]["error"]["code"] == "SNAPSHOT_REVISION_CONFLICT"


def test_snapshot_sync_sends_full_then_validated_diff():
    sync = SnapshotSync()
    first = sync.prepare({"activeSpec": {"id": 1}, "config": {"enemy": "boss"}})
    second = sync.prepare({"activeSpec": {"id": 1}, "config": {"enemy": "rare"}})
    assert first["mode"] == "full" and first["snapshot"]
    assert second["mode"] == "diff"
    assert second["diff"]["baseRevision"] == first["snapshotRevision"]
    assert second["diff"]["changes"]["config"]["after"]["enemy"] == "rare"


def test_stale_plan_is_rejected_before_handler():
    called = []
    result = execute_plan("q", {"steps": [{"tool": "get_skill_stats", "arguments": {}, "expectedSnapshotRevision": "old"}]}, handlers={"get_skill_stats": lambda args: called.append(args)}, snapshot_revision_value="new")
    assert not called
    assert result["steps"][0]["error"]["code"] == "SNAPSHOT_REVISION_CONFLICT"


def test_bare_tool_result_is_explicitly_unverified():
    result = execute_plan("q", {"steps": [{"tool": "get_skill_stats", "arguments": {}}]}, handlers={"get_skill_stats": lambda args: {"facts": {"value": 10}}})
    assert result["steps"][0]["uncertainty"]["reason"] == "missing_evidence_graph"


def test_external_provider_requires_remote_configuration():
    with pytest.raises(ValueError):
        OpenAICompatibleClient()
    with pytest.raises(ValueError):
        OpenAICompatibleClient(endpoint="http://127.0.0.1:11434/v1", model="qwen")
    client = OpenAICompatibleClient(endpoint="https://agent.example.invalid/v1", model="external-model")
    assert client.endpoint.startswith("https://")


def test_agent_loop_sends_normalized_context_not_raw_xml():
    class Model:
        def __init__(self):
            self.messages = []

        def chat(self, messages):
            self.messages.append(messages)
            if len(self.messages) == 1:
                return '{"intent":"stat","steps":[{"tool":"get_skill_stats","arguments":{}}]}'
            return "근거를 확인할 수 없습니다."

    model = Model()
    result = AgentLoop(model).run("스킬 수치", snapshot={"xml": "secret", "config": {"enemy": "boss"}}, handlers={"get_skill_stats": lambda args: {"evidenceGraph": {"nodes": []}, "facts": {}}})
    assert result["status"] == "ok"
    planning_text = model.messages[0][1]["content"]
    assert "secret" not in planning_text and "xml" not in planning_text
