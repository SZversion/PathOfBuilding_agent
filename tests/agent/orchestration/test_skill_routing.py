import json

import pytest

from agent.orchestration.agent_loop import AgentLoop
from agent.orchestration.skills import discover_skills, selected_instructions


@pytest.mark.parametrize("names", [["lookup"], ["compare"], ["lookup", "compare"], []])
def test_selection_receives_only_metadata_and_injects_selected_body(names):
    class Model:
        supports_json_schema = True

        def __init__(self):
            self.messages = []

        def chat(self, messages, **kwargs):
            self.messages.append(messages)
            if len(self.messages) == 1:
                payload = json.loads(messages[1]["content"])
                assert set(payload["skills"][0]) == {"name", "description"}
                assert "Use get_highest_dps_skill" not in json.dumps(messages)
                assert kwargs["format"]["properties"]["skills"]["items"]["enum"] == sorted(discover_skills())
                return json.dumps({"skills": names})
            if len(self.messages) == 2:
                assert ("Use get_highest_dps_skill" in messages[0]["content"]) == ("lookup" in names)
                assert ("# Changes and comparisons" in messages[0]["content"]) == ("compare" in names)
                assert json.loads(messages[1]["content"])["selected_skills"] == names
                return json.dumps({"schema_version": "1.0", "intent": "stat", "operation": "read",
                                   "evidenceLevel": "calculated", "ambiguities": [],
                                   "steps": [{"tool": "get_character_stats", "arguments": {}}]})
            assert ("Use get_highest_dps_skill" in messages[0]["content"]) == ("lookup" in names)
            assert ("# Changes and comparisons" in messages[0]["content"]) == ("compare" in names)
            return "Life: 100"

    model = Model()
    result = AgentLoop(model).run("life?", handlers={"get_character_stats": lambda args: {"facts": {"life": 100}}})
    assert result["status"] == "ok"
    assert len(model.messages) == 3
    generations = [event for event in result["trace"] if event["event"] == "provider_completed"]
    assert len(generations) == 3


@pytest.mark.parametrize("selection", [{"skills": ["../common"]}, {"skills": ["lookup", "lookup"]}, {"skills": "lookup"}])
def test_invalid_selection_never_loads_a_body(selection):
    with pytest.raises(ValueError):
        selected_instructions(selection, discover_skills())


def test_invalid_selection_is_repaired_before_any_tool_executes():
    calls = []

    class Model:
        def chat(self, messages):
            calls.append(messages)
            if len(calls) == 1:
                return '{"skills":["unavailable"]}'
            if len(calls) == 2:
                assert "repair_feedback" in json.loads(messages[1]["content"])
                return '{"skills":["lookup"]}'
            if len(calls) == 3:
                return '{"schema_version":"1.0","intent":"stat","operation":"read","evidenceLevel":"calculated","steps":[{"tool":"get_character_stats","arguments":{}}]}'
            return "Life: 100"

    def handler(args):
        assert len(calls) == 3
        return {"facts": {"life": 100}}

    result = AgentLoop(Model()).run("life?", handlers={"get_character_stats": handler})
    assert result["status"] == "ok"
    assert len(calls) == 4
