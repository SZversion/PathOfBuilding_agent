import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop, PLANNER_JSON_SCHEMA, PlanValidationError, normalize_query, planner_query_projection, resolve_active_context, validate_plan


def test_query_schema_normalizes_legacy_and_validates_enums():
    assert normalize_query("Arc DPS")["schema_version"] == "1.0"
    query = normalize_query({"text": "Arc", "intent": "projectile", "operation": "read", "evidenceLevel": "calculated"})
    assert query["required_evidence"] == []
    assert {"subject", "context", "ambiguities", "confidence", "requires"} <= set(query)
    assert normalize_query({"text": "Arc", "confidence": 0.8, "requires": ["skill"]})["confidence"] == 0.8
    with pytest.raises(PlanValidationError):
        normalize_query({"text": "Arc", "operation": "not-an-operation"})


def test_planner_projection_excludes_query_inference_fields():
    query = normalize_query("dps가 가장 높은 스킬이 뭐야?")
    projected = planner_query_projection(query, context={"snapshotRevision": "rev-1", "activeSkillSet": "Default"})
    assert projected["question"] == "dps가 가장 높은 스킬이 뭐야?"
    assert projected["text"] == projected["question"]
    assert projected["context"]["snapshotRevision"] == "rev-1"
    assert not ({"intent", "operation", "evidenceLevel", "required_evidence", "subject", "ambiguities", "confidence", "requires"} & set(projected))


def test_active_context_selection_prefers_pob_state_and_unique_candidates():
    context = {
        "activeSkillSet": {"id": "b", "title": "Endgame"},
        "skillSets": {"a": {"title": "Leveling"}, "b": {"title": "Endgame"}},
        "itemSets": [{"id": "items-1", "title": "Mapping"}],
        "specs": {"spec-1": {"title": "Default"}, "spec-2": {"title": "Boss"}},
        "activeSpec": {"id": "spec-2", "title": "Boss"},
    }
    selection = resolve_active_context(context)
    assert selection["selected"]["skillSet"]["id"] == "b"
    assert selection["selected"]["itemSet"]["id"] == "items-1"
    assert selection["selected"]["treeSpec"]["id"] == "spec-2"
    assert selection["conflicts"] == []
    projected = planner_query_projection(normalize_query("DPS"), context=context)
    assert projected["contextSelection"] == selection


def test_context_selection_conflict_stops_before_planner():
    class MustNotRun:
        def __init__(self): self.calls = 0
        def chat(self, messages, **kwargs):
            self.calls += 1
            raise AssertionError("planner must not run for conflicting context")

    model = MustNotRun()
    result = AgentLoop(model).run("dps?", snapshot={
        "activeSkillSet": None,
        "skillSets": {"a": {"title": "One"}, "b": {"title": "Two"}},
    })
    assert model.calls == 0
    assert result["error"]["error_ref"] == "AMBIGUOUS_CONTEXT"
    assert result["error"]["recovery_class"] == "ASK_USER"
    assert result["error"]["details"]["missing_fields"] == ["skillSet"]


def test_request_local_item_set_override_preserves_unmentioned_active_context():
    context = {
        "activeSkillSet": {"id": "skill-active", "title": "Mapping"},
        "skillSets": {"skill-active": {"title": "Mapping"}, "skill-other": {"title": "Boss"}},
        "activeItemSet": {"id": "items-active", "title": "Mapping"},
        "itemSets": [{"id": "items-active", "title": "Mapping"}, {"id": "items-boss", "title": "Boss"}],
        "activeSpec": {"id": "spec-active", "title": "Mapping"},
        "specs": {"spec-active": {"title": "Mapping"}, "spec-boss": {"title": "Boss"}},
    }
    projected = planner_query_projection(normalize_query("2번 장비셋으로 DPS 비교"), context=context)
    selection = projected["contextSelection"]["selected"]
    assert selection["itemSet"]["id"] == "items-boss"
    assert selection["itemSet"]["source"] == "사용자 질문"
    assert selection["skillSet"]["id"] == "skill-active"
    assert selection["treeSpec"]["id"] == "spec-active"
    assert projected["contextSelection"]["conflicts"] == []


def test_request_local_unsupported_item_set_is_marked_for_user_clarification():
    context = {"itemSets": [{"id": "items-active", "title": "Mapping"}, {"id": "items-boss", "title": "Boss"}], "activeItemSet": {"id": "items-active"}}
    projected = planner_query_projection(normalize_query("99번 장비셋으로 계산"), context=context)
    assert "itemSet" in projected["contextSelection"]["conflicts"]


def test_dps_question_planner_payload_has_no_inferred_defaults():
    captured = []

    class Model:
        def chat(self, messages, **kwargs):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                captured.append(json.loads(messages[1]["content"]))
                return '{"schema_version":"1.0","intent":"stat","operation":"read","evidenceLevel":"calculated","steps":[{"tool":"get_highest_dps_skill","arguments":{}}]}'
            return "결과"

    result = AgentLoop(Model()).run("dps가 가장 높은 스킬이 뭐야?", handlers={"get_highest_dps_skill": lambda args: {"facts": {"skill": "Arc"}, "evidenceGraph": {"nodes": []}}})
    assert captured and captured[0]["question"] == "dps가 가장 높은 스킬이 뭐야?"
    assert "query" not in captured[0]
    assert not {"intent", "operation", "evidenceLevel", "required_evidence", "subject", "ambiguities", "confidence", "requires"} & set(captured[0])


def test_plan_schema_defaults_and_completeness_registry():
    legacy = validate_plan({"intent": "stat", "steps": []})
    assert legacy["schema_version"] == "1.0" and legacy["operation"] == "answer"
    with pytest.raises(PlanValidationError) as missing:
        validate_plan({"schema_version": "1.0", "intent": "projectile", "operation": "read", "evidenceLevel": "calculated", "steps": []})
    assert missing.value.code == "PLAN_INCOMPLETE"
    complete = validate_plan({"schema_version": "1.0", "intent": "projectile", "operation": "read", "evidenceLevel": "calculated", "required_evidence": ["calculated"], "steps": [{"tool": "get_projectile_count", "arguments": {}}]})
    assert complete["steps"][0]["tool"] == "get_projectile_count"
    with pytest.raises(PlanValidationError) as evidence:
        validate_plan({"schema_version": "1.0", "intent": "mechanism", "operation": "explain", "evidenceLevel": "mixed", "steps": [{"tool": "resolve_skill_context", "arguments": {}}]})
    assert evidence.value.code == "PLAN_INCOMPLETE"
    legacy_mechanism = validate_plan({"intent": "mechanism", "steps": [{"tool": "resolve_skill_context", "arguments": {}}]})
    assert legacy_mechanism["intent"] == "mechanism"


def test_planner_schema_version_is_exact_and_validator_reports_details():
    assert PLANNER_JSON_SCHEMA["properties"]["schema_version"] == {"type": "string", "const": "1.0"}
    with pytest.raises(PlanValidationError) as invalid:
        validate_plan({"schema_version": "2.0", "intent": "stat", "steps": []})
    assert invalid.value.details == {"field": "schema_version", "expected": "1.0", "actual": "2.0"}


def test_two_layer_query_and_plan_refs_and_evidence_gate():
    class Model:
        def __init__(self):
            self.final_called = False

        def chat(self, messages):
            if messages[0]["role"] == "system" and "planner" in messages[0]["content"]:
                return '{"schema_version":"1.0","intent":"projectile","operation":"read","evidenceLevel":"calculated","required_evidence":["calculated"],"steps":[{"tool":"get_projectile_count","arguments":{}}]}'
            self.final_called = True
            return "추측 답변"

    model = Model()
    result = AgentLoop(model).run("Arc 투사체", handlers={"get_projectile_count": lambda args: {"facts": {"value": 3}}})
    assert result["status"] == "partial"
    assert model.final_called is False
    assert result["uncertainty"]["code"] == "EVIDENCE_INCOMPLETE"
    planner_start = next(event for event in result["trace"] if event["event"] == "planner_started")
    planner_done = next(event for event in result["trace"] if event["event"] == "planner_completed")
    assert planner_start["query_ref"].startswith("query:")
    assert planner_done["query_ref"].startswith("query:") and planner_done["plan_ref"].startswith("plan:")


def test_ambiguity_is_terminal_and_planner_is_bounded_to_five_attempts():
    class Ambiguous:
        def chat(self, messages):
            return '{"schema_version":"1.0","intent":"unknown","operation":"answer","evidenceLevel":"any","stop_condition":{"type":"ask_user"},"steps":[]}'

    ambiguous = AgentLoop(Ambiguous()).run("Arc")
    assert ambiguous["error"]["code"] == "AMBIGUOUS_ALIAS"
    assert ambiguous["error"]["error_ref"] == "AMBIGUOUS_CONTEXT"
    assert ambiguous["error"]["next_action"] == "ask_user"
    terminal = next(event for event in ambiguous["trace"] if event["event"] == "run_completed")
    assert terminal["error_ref"] == "AMBIGUOUS_CONTEXT" and terminal["error_code"] == "AMBIGUOUS_ALIAS"

    class Broken:
        def __init__(self):
            self.calls = 0

        def chat(self, messages):
            self.calls += 1
            return "not json"

    broken_model = Broken()
    broken = AgentLoop(broken_model).run("Arc")
    assert broken_model.calls == 5
    assert broken["error"]["code"] == "REPAIR_INPUT"
    assert broken["error"]["max_attempts"] == 5


def test_unknown_or_ambiguity_without_ask_user_is_terminal():
    with pytest.raises(PlanValidationError) as unknown:
        validate_plan({"schema_version": "1.0", "intent": "unknown", "steps": []})
    assert unknown.value.code == "AMBIGUOUS_ALIAS"
    with pytest.raises(PlanValidationError) as ambiguous:
        validate_plan({"schema_version": "1.0", "intent": "stat", "ambiguities": ["which skill"], "steps": []})
    assert ambiguous.value.code == "AMBIGUOUS_ALIAS"


def test_live_envelope_defaults_and_explicit_set_priority():
    context = {"facts": {"activeSkillSet": {"id": 7, "title": "Mapping"},
        "activeConfigSet": {"id": 2, "title": "Boss"}, "mainSkill": {"name": "Arc"},
        "config": {"enemyIsBoss": "Pinnacle"},
        "availableSkillSets": [{"id": 7, "title": "Mapping"}, {"id": 3, "title": "Boss"}],
        "availableConfigSets": [{"id": 2, "title": "Boss"}]}}
    defaults = resolve_active_context(context, text="highest DPS skill")
    assert defaults["selected"]["skillSet"]["id"] == 7
    assert defaults["selected"]["mainSkill"]["name"] == "Arc"
    assert defaults["selected"]["config"]["enemyIsBoss"] == "Pinnacle"
    explicit = resolve_active_context(context, text="2번 스킬셋 DPS")
    assert explicit["selected"]["skillSet"]["id"] == 3
    assert explicit["selected"]["configSet"]["id"] == 2
    assert explicit["conflicts"] == []
    named = resolve_active_context(context, text="Boss skill set DPS")
    assert named["selected"]["skillSet"]["id"] == 3
    missing = resolve_active_context(context, text="99번 스킬셋 DPS")
    assert missing["conflicts"] == ["skillSet"]


def test_explicit_set_reaches_tool_without_changing_other_defaults():
    calls = []
    class Model:
        def chat(self, messages, **kwargs):
            if "planner" in messages[0]["content"]:
                payload = json.loads(messages[1]["content"])
                assert payload["contextSelection"]["selected"]["skillSet"]["id"] == 3
                assert payload["contextSelection"]["selected"]["mainSkill"]["name"] == "Arc"
                return '{"schema_version":"1.0","intent":"stat","operation":"read","evidenceLevel":"calculated","steps":[{"tool":"get_highest_dps_skill","arguments":{}}]}'
            return "Arc"
    result = AgentLoop(Model()).run("2번 스킬셋 DPS", snapshot={"activeSkillSet": {"id": 7},
        "mainSkill": {"name": "Arc"}, "availableSkillSets": [{"id": 7}, {"id": 3}]},
        handlers={"get_highest_dps_skill": lambda args: calls.append(args) or {"facts": {"skill": "Arc"}}})
    assert result["status"] == "ok"
    assert calls[0]["contextOverrides"] == {"activeSkillSet": 3}


def test_planner_repairs_clarification_for_a_known_live_skill():
    class Model:
        calls = 0
        def chat(self, messages, **kwargs):
            if "planner" in messages[0]["content"]:
                self.calls += 1
                payload = json.loads(messages[1]["content"])
                if self.calls == 1:
                    return '{"steps":[],"ambiguities":["skill_id:Arc"]}'
                assert payload["repair_feedback"]["details"]["already_available"] == ["skill_id:Arc"]
                return '{"schema_version":"1.0","intent":"stat","operation":"read","evidenceLevel":"calculated","steps":[{"tool":"get_highest_dps_skill","arguments":{}}]}'
            return "Arc"
    model = Model()
    result = AgentLoop(model).run("highest DPS skill", snapshot={"calculatedSnapshot": {"skills": [{"name": "Arc"}]}, "mainSkill": {"name": "Arc"}},
        handlers={"get_highest_dps_skill": lambda args: {"facts": {"skill": "Arc"}}})
    assert result["status"] == "ok" and model.calls == 2
