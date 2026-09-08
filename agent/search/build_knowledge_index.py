"""Build the local search index from aliases plus semantic rule files."""
import json
import re
from pathlib import Path


def _tokens(value):
    return sorted(set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)))


def build(index_path):
    index_path = Path(index_path)
    root = index_path.parents[1]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    documents = [d for d in index.get("documents", []) if not d.get("ruleId")]
    fixture_path = root / "fixtures" / "index.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))["fixtures"] if fixture_path.exists() else []
    for path in sorted((root / "rules").glob("*.json")):
        if path.name == "schema.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for rule in payload.get("rules", []):
            verification = rule.get("verification")
            verification_state = verification if isinstance(verification, str) else (verification or {}).get("state", "unverified")
            status = rule.get("status", verification_state)
            fixture_refs = [f["id"] for f in fixtures if rule.get("id") in f.get("ruleIds", [])]
            text = rule.get("statement", "")
            terms = " ".join(rule.get("terms", []))
            search_text = f"{text} {terms} {rule.get('category', '')} {rule.get('id', '')}"
            documents.append({
                "text": text,
                "korean": None,
                "category": rule.get("category", payload.get("domain", "rule")),
                "source": str(path.relative_to(root.parent)).replace("\\", "/"),
                "ruleId": rule.get("id"),
                "status": status,
                "verification": verification,
                "gamePatch": rule.get("gamePatch", payload.get("gamePatch")),
                "scope": rule.get("scope"),
                "domain": rule.get("domain"),
                "pobVersion": rule.get("pobVersion"),
                "dataRevision": rule.get("dataRevision"),
                "sources": rule.get("sources", []),
                "uncertainty": rule.get("uncertainty", {}),
                "pobEvidence": rule.get("pobEvidence"),
                "relatedRuleIds": rule.get("relatedRuleIds", []),
                "dependencies": rule.get("dependencies", []),
                "interactions": rule.get("interactions", []),
                "sourceEdges": rule.get("sourceEdges", []),
                "fixtureRefs": fixture_refs,
                "versionUnknown": rule.get("gamePatch", payload.get("gamePatch")) is None,
                "searchText": search_text.casefold(),
                "tokens": _tokens(search_text),
            })
    index["documents"] = documents
    index["ruleIndex"] = {"authoritativeStatuses": ["canonical", "fixture_verified", "verified"], "nonAuthoritativeStatuses": ["planned", "draft", "unverified", "partial", "conflict", "needs_patch_check"]}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).parents[1] / "knowledge" / "index" / "poe1-3.29.json")
