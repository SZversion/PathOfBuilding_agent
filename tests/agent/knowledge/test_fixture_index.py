import json
from pathlib import Path


def test_fixture_index_has_version_context_and_documents():
    root = Path(__file__).parents[3]
    payload = json.loads((root / "agent/knowledge/fixtures/index.json").read_text(encoding="utf-8"))
    assert payload["fixtures"]
    for fixture in payload["fixtures"]:
        assert fixture["id"] and fixture["document"]
        assert fixture["gamePatch"]
        assert fixture["status"] in {"observed", "partial", "verified"}
