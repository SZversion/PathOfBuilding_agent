import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.runtime import execute, execute_plan, run_question


class FakeSearch:
    def __init__(self):
        self.calls = []

    def search(self, query, limit=10, category=None):
        self.calls.append((query, limit, category))
        return [{"text": "Resistance rule", "score": 11}]


search = FakeSearch()
result = run_question("저항 규칙을 알려줘", search=search)
assert result["steps"][0]["status"] == "ok"
assert result["steps"][0]["result"][0]["text"] == "Resistance rule"
assert search.calls == [("저항 규칙을 알려줘", 10, None)]

order = []
result = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "first", "arguments": {"value": 1}},
    {"tool": "second", "arguments": {"value": 2}},
]}, handlers={"first": lambda args: order.append(args["value"]) or "a",
              "second": lambda args: order.append(args["value"]) or "b"})
assert order == [1, 2]
assert [step["status"] for step in result["steps"]] == ["ok", "ok"]

unavailable = run_question("투사체 개수가 몇 개야?")
assert unavailable["steps"][0]["status"] == "unavailable"

failed = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "broken", "arguments": {}},
    {"tool": "bad_args", "arguments": []},
    {"tool": "missing_args"},
]}, handlers={"broken": lambda args: (_ for _ in ()).throw(RuntimeError("boom"))})
assert failed["steps"][0] == {"tool": "broken", "status": "error", "error": "boom"}
assert failed["steps"][1]["error"] == "arguments must be a dict"
assert failed["steps"][2]["error"] == "arguments are required"
assert execute is execute_plan

print("orchestration runtime self-check passed")
