import json
import pathlib
import sys

import jsonschema
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration import agent_loop
from agent.orchestration.agent_loop import AgentLoop, PlanValidationError, _load_planner_schema


def _validate_planner_output(*args, **kwargs):
    return agent_loop._validate_planner_output(*args, **kwargs)


def plan(tool="search_external", arguments=None):
    return {"schema_version": "1.0", "intent": "search", "operation": "search", "evidenceLevel": "external",
            "required_evidence": [], "stop_condition": {"type": "answer"}, "ambiguities": [],
            "steps": [{"tool": tool, "arguments": arguments if arguments is not None else {"query": "Arc", "source": "poewiki"}, "expectedSnapshotRevision": None}]}


@pytest.mark.parametrize("field", ["schema_version", "intent", "operation", "evidenceLevel", "required_evidence", "stop_condition", "ambiguities", "steps"])
def test_model_output_requires_all_contract_fields(field):
    value = plan()
    del value[field]
    with pytest.raises(PlanValidationError) as error:
        _validate_planner_output(value)
    assert error.value.code == "MODEL_SCHEMA_INVALID"


@pytest.mark.parametrize("arguments", [{"query": "Arc", "source": "https://example.com"}, {"query": "Arc", "limit": 4}, {"query": "Arc", "limit": True}, {"query": " "}, {"query": "Arc", "skillName": "Arc"}])
def test_tool_specific_argument_constraints(arguments):
    value = plan(arguments=arguments)
    assert list(jsonschema.Draft202012Validator(_load_planner_schema()).iter_errors(value))
    with pytest.raises(PlanValidationError) as error:
        _validate_planner_output(value)
    assert error.value.code == "MODEL_SCHEMA_INVALID"
    assert error.value.details["fields"][0].startswith("/steps/0/arguments")


@pytest.mark.parametrize("field,value", [("intent", "invented"), ("operation", "invented"), ("evidenceLevel", "invented"), ("required_evidence", ["invented"]), ("required_evidence", ["calculated", "calculated"]), ("stop_condition", {"max_steps": 8}), ("stop_condition", {"type": "answer", "selected_skills": ["lookup"]}), ("metadata", {}), ("extra", 1)])
def test_top_level_constraints(field, value):
    output = plan()
    output[field] = value
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output)


def test_normal_and_clarification_plans_have_distinct_contracts():
    output = plan("get_skill_dps", {"skillName": None})
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output)
    output.update(intent="unknown", stop_condition={"type": "ask_user"}, ambiguities=["/steps/0/arguments/skillName"])
    _validate_planner_output(output)
    output["steps"][0]["arguments"]["skillSetSelector"] = None
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output)


def test_revision_and_step_fields_are_checked():
    output = plan()
    _validate_planner_output(output, snapshot_revision="rev-current")
    output["steps"][0]["expectedSnapshotRevision"] = "rev-old"
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output, snapshot_revision="rev-current")
    output["steps"][0]["expectedSnapshotRevision"] = "rev-current"
    _validate_planner_output(output, snapshot_revision="rev-current")
    output["steps"][0]["extra"] = True
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output)


@pytest.mark.parametrize("tool,arguments", [("get_duration", {"skillName": "Arc", "durationType": "skill"}), ("get_item_modifiers", {"itemId": 1})])
def test_catalog_arguments_survive_execution_validation(tool, arguments):
    output = plan(tool, arguments)
    _validate_planner_output(output)
    assert agent_loop.validate_plan(output)["steps"][0]["arguments"] == arguments


def test_schema_tracks_configured_step_limit(monkeypatch):
    from agent.orchestration import agent_loop
    monkeypatch.setattr(agent_loop, "MAX_STEPS", 2)
    output = plan()
    output["steps"] *= 3
    with pytest.raises(PlanValidationError):
        _validate_planner_output(output)


def test_model_receives_strict_schema_and_repairs_invalid_source():
    seen = []

    class Model:
        supports_json_schema = True

        def chat(self, messages, **kwargs):
            payload = json.loads(messages[1]["content"])
            if "skills" in payload:
                return '{"skills":[]}'
            if "planner" in messages[0]["content"]:
                seen.append(payload)
                output = plan("get_skill_dps", {"skillName": "Arc"})
                if len(seen) == 1:
                    return json.dumps(plan(arguments={"query": "Arc", "source": "https://example.com"}))
                feedback = payload["repair_feedback"]
                assert feedback["code"] == "MODEL_SCHEMA_INVALID"
                assert feedback["details"]["fields"] == ["/steps/0/arguments/source"]
                assert feedback["details"]["expected"] == ["poedb", "poewiki", "both"]
                jsonschema.validate(output, kwargs["format"])
                return json.dumps(output)
            return "Arc DPS"

    calls = []
    result = AgentLoop(Model()).run("Arc DPS", handlers={"get_skill_dps": lambda args: calls.append(args) or {"facts": {"value": 1}}})
    assert result["status"] == "ok"
    assert len(seen) == 2
    assert calls == [{"skillName": "Arc"}]
