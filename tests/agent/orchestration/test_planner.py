import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))
from agent.orchestration.planner import plan


assert plan("모루 한국어 이름 아이템 찾아줘")["intent"] == "item_alias"
assert plan("투사체 개수가 몇 개야?")["steps"][0]["tool"] == "get_projectile_count"
assert plan("저주 한도는 몇 개야?")["steps"][0]["tool"] == "get_curse_limit"
comparison = plan("Greater Volley를 끄면 Poisonous Concoction of Bouncing 딜이 왜 줄어?")
assert comparison["intent"] == "mechanism_compare"
assert [step["tool"] for step in comparison["steps"]] == ["compare_support_effect", "explain_damage_change"]
assert plan("zzzzzzzz qwerty")["intent"] == "unknown"
print("orchestration planner self-check passed")
