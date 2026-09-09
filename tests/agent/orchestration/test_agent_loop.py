import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.agent_loop import ALLOWED_TOOLS, AgentLoop, validate_plan
from agent.orchestration.runtime import execute_plan
from agent.pob.bridge import MAX_TOOL_ATTEMPTS, PobBridgeError

assert {"get_character_stats", "get_skill_stats"}.issubset(ALLOWED_TOOLS)
assert "compare_build_states" in ALLOWED_TOOLS

calls = {"count": 0}
def always_timeout(args):
    calls["count"] += 1
    raise PobBridgeError("timeout", "TIMEOUT")
structured = execute_plan("질문", {"intent": "x", "steps": [{"tool": "x", "arguments": {}}]}, handlers={"x": always_timeout})
assert structured["steps"][0]["error"]["code"] == "TIMEOUT"
assert structured["steps"][0]["error"]["recovery_class"] == "RETRY_TOOL"
assert calls["count"] == MAX_TOOL_ATTEMPTS
assert structured["steps"][0]["error"]["attempt"] == MAX_TOOL_ATTEMPTS
assert structured["steps"][0]["error"]["max_attempts"] == MAX_TOOL_ATTEMPTS

# A stale mutation is discarded once and is never retried or applied.
mutation_calls = {"count": 0}
def stale_mutation(args):
    mutation_calls["count"] += 1
    raise PobBridgeError("stale", "SNAPSHOT_REVISION_CONFLICT")
stale = execute_plan("교체", {"intent": "mutation", "steps": [{"tool": "replace_item", "arguments": {"expectedSnapshotRevision": "old"}}]}, handlers={"replace_item": stale_mutation})
assert mutation_calls["count"] == 1
assert stale["steps"][0]["error"]["code"] == "SNAPSHOT_REVISION_CONFLICT"
assert stale["steps"][0]["error"]["max_attempts"] == 1

timeout_calls = {"count": 0}
def uncertain_mutation(args):
    timeout_calls["count"] += 1
    from agent.pob.bridge import PobTimeoutError
    raise PobTimeoutError("mutation timeout")
uncertain = execute_plan("교체", {"intent": "mutation", "steps": [{"tool": "replace_gem", "arguments": {}}]}, handlers={"replace_gem": uncertain_mutation})
assert timeout_calls["count"] == 1
assert uncertain["steps"][0]["error"]["code"] == "MUTATION_TIMEOUT"
assert uncertain["steps"][0]["error"]["recovery_class"] == "REFRESH_CONTEXT"
assert uncertain["steps"][0]["error"]["next_action"] == "recapture_snapshot"

budget_steps = [{"tool": f"tool_{index}", "arguments": {}} for index in range(9)]
budget_calls = {"count": 0}
def budget_handler(args):
    budget_calls["count"] += 1
    return {"ok": True}
budget = execute_plan("예산", {"intent": "many", "steps": budget_steps}, handlers={f"tool_{index}": budget_handler for index in range(9)})
assert budget["tool_call_count"] == 8 and budget_calls["count"] == 8
assert budget["steps"][-1]["status"] == "human_review"
assert budget["steps"][-1]["error"]["code"] == "RETRY_EXHAUSTED"

for code in ("INPUT_INVALID", "VALUE_UNAVAILABLE", "SNAPSHOT_REVISION_CONFLICT"):
    calls["count"] = 0
    def terminal_failure(args, code=code):
        calls["count"] += 1
        raise PobBridgeError("terminal", code)
    structured = execute_plan("질문", {"intent": "x", "steps": [{"tool": "x", "arguments": {}}]}, handlers={"x": terminal_failure})
    assert calls["count"] == 1
    assert structured["steps"][0]["error"]["max_attempts"] == 1


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
assert "answer in Korean" in model.calls[1][0]["content"] and "friendly" in model.calls[1][0]["content"]

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
