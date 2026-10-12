import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

from agent.orchestration.runtime import execute, execute_plan, run_question
from agent.mcp.errors import ToolCallError


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
assert failed["steps"][0]["error"]["code"] == "TOOL_EXECUTION_ERROR"
assert failed["steps"][0]["error"]["message"] == "boom"
assert failed["steps"][1]["error"]["code"] == "INPUT_INVALID"
assert failed["steps"][2]["error"]["code"] == "INPUT_INVALID"
assert execute is execute_plan

attempts = {"count": 0}
def transient_mcp_tool(args):
    attempts["count"] += 1
    if attempts["count"] == 1:
        raise ToolCallError({"error_code": "TOOL_TRANSIENT", "recovery_class": "RETRY_TOOL",
                             "retryable": True, "attempt": 1, "max_attempts": 2, "message": "temporary"})
    return {"facts": {"dps": 10}}

retried = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "get_skill_dps", "arguments": {"skillIndex": 1}},
]}, handlers={"get_skill_dps": transient_mcp_tool})
assert attempts["count"] == 2
assert retried["steps"][0]["attempt"] == 2

search_attempts = {"count": 0}
class RetryableMcpSearch:
    def search(self, query, limit=10, category=None):
        search_attempts["count"] += 1
        if search_attempts["count"] == 1:
            raise ToolCallError({"error_code": "RAG_TRANSIENT", "recovery_class": "RETRY_TOOL",
                                 "retryable": True, "attempt": 1, "max_attempts": 2, "message": "temporary"})
        return {"facts": {"matches": []}}

retried_search = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "search_knowledge", "arguments": {"query": "ignite"}},
]}, search=RetryableMcpSearch())
assert search_attempts["count"] == 2
assert retried_search["steps"][0]["attempt"] == 2

ambiguous_attempts = {"count": 0}
class AmbiguousSearch:
    def resolve_skill_alias(self, query):
        ambiguous_attempts["count"] += 1
        raise ValueError("skill alias is ambiguous")

ambiguous = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "resolve_skill_alias", "arguments": {"query": "test"}},
]}, search=AmbiguousSearch())
assert ambiguous_attempts["count"] == 1
assert ambiguous["steps"][0]["error"]["error_code"] == "AMBIGUOUS_ALIAS"
assert ambiguous["steps"][0]["error"]["recovery_class"] == "ASK_USER"

mutation_attempts = {"count": 0}
def rejected_mutation(args):
    mutation_attempts["count"] += 1
    raise ToolCallError({"error_code": "MUTATION_NOT_PERSISTENT", "recovery_class": "REJECT",
                         "retryable": False, "max_attempts": 1, "message": "blocked"})

mutation = execute_plan("x", {"intent": "test", "steps": [
    {"tool": "replace_gem", "arguments": {"socketGroup": 1}},
]}, handlers={"replace_gem": rejected_mutation})
assert mutation_attempts["count"] == 1
assert mutation["steps"][0]["error"]["error_code"] == "MUTATION_NOT_PERSISTENT"

print("orchestration MCP retry self-check passed")

print("orchestration runtime self-check passed")
