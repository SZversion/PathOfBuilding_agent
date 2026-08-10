import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import AgentLoop, validate_plan


class FakeModel:
    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        if len(self.calls) == 1:
            return '{"intent":"pob_stat","steps":[{"tool":"get_curse_limit","arguments":{}}]}'
        return "저주 한도는 Tool 결과를 기준으로 설명합니다."


model = FakeModel()
result = AgentLoop(model).run("저주 한도는 몇 개야?", handlers={"get_curse_limit": lambda args: {"facts": {"value": 2}}})
assert result["status"] == "ok" and result["execution"]["steps"][0]["status"] == "ok"
assert len(model.calls) == 2 and result["answer"].startswith("저주 한도")
assert "한국어" in model.calls[1][0]["content"] and "친절" in model.calls[1][0]["content"]

for bad in (
    {"steps": [{"tool": "not_allowed", "arguments": {}}]},
    {"steps": [{"tool": "get_curse_limit", "arguments": {}}, {"tool": "get_curse_limit", "arguments": {}}]},
    {"steps": [{"tool": "get_curse_limit", "arguments": []}]},
):
    try:
        validate_plan(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid plan accepted")

bad_model = type("BadModel", (), {"chat": lambda self, messages: "not json"})()
assert AgentLoop(bad_model).run("질문")["status"] == "plan_error"
print("model agent loop self-check passed")
