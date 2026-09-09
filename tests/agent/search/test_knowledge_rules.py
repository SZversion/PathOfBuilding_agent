import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
RULES = ROOT / "agent" / "knowledge" / "rules"


def test_rule_json_and_semantic_fields_are_valid():
    for path in RULES.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for rule in payload.get("rules", []):
            assert rule["id"]
            assert isinstance(rule.get("sources", []), list)
            assert isinstance(rule.get("verification", payload.get("status", "unverified")), (str, dict))
            if "relatedRuleIds" in rule:
                assert all(isinstance(value, str) for value in rule["relatedRuleIds"])
            if rule.get("status") in {"planned", "draft", "unverified", "conflict"}:
                assert rule.get("pobEvidence") in (None, [], {}) or rule.get("verification", {}).get("state") != "canonical"
