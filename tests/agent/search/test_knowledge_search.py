import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))
from agent.search.knowledge_search import KnowledgeSearch


searcher = KnowledgeSearch("agent/knowledge/index/poe1-3.29.json")

result = searcher.search("The Anvil", limit=1)
assert result and result[0]["korean"] == "모루"
result = searcher.search("파란 진주 목걸이", limit=1)
assert result and result[0]["text"] == "Blue Pearl Amulet"
assert searcher.search("모루", category="item.base_type") == []
assert searcher.search("파란 진주 목걸이", category="item.base_type")
assert searcher.search("zzzzzzzz-qwerty") == []
print("knowledge search self-check passed")
