import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop, PlanValidationError, normalize_query, validate_plan


def test_query_schema_normalizes_legacy_and_validates_enums():
    assert normalize_query("Arc DPS")["schema_version"] == "1.0"
    query = normalize_query({"text": "Arc", "intent": "projectile", "operation": "read", "evidenceLevel": "calculated"})
    assert query["required_evidence"] == []
    assert {"subject", "context", "ambiguities", "confidence", "requires"} <= set(query)
    assert normalize_query({"text": "Arc", "confidence": 0.8, "requires": ["skill"]})["confidence"] == 0.8
    with pytest.raises(PlanValidationError):
        normalize_query({"text": "Arc", "operation": "not-an-operation"})


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
    assert ambiguous["error"]["next_action"] == "ask_user"

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
