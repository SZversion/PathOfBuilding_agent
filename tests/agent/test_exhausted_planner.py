import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from agent.orchestration.agent_loop import AgentLoop
from agent.orchestration.recovery import EXHAUSTED_ANSWER


def test_planner_provider_failures_return_fixed_exhausted_answer():
    class Broken:
        def chat(self, messages, **kwargs):
            raise RuntimeError("planner unavailable")

    result = AgentLoop(Broken()).run("life?")
    assert result["status"] == "plan_error"
    assert result["answer"] == EXHAUSTED_ANSWER
    assert result["error"]["attempt"] == 5
    assert result["error"]["max_attempts"] == 5
    assert result["trace"][-1]["event"] == "run_completed"
