import json
import re
from pathlib import Path


def _tokens(value):
    return set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE))


class KnowledgeSearch:
    def __init__(self, index_path):
        with open(index_path, encoding="utf-8") as stream:
            self.documents = json.load(stream)["documents"]
        alias_path = Path(index_path).parents[1] / "aliases" / "ko" / "skills-3.29.json"
        self.skill_aliases = json.loads(alias_path.read_text(encoding="utf-8"))["entries"] if alias_path.exists() else []

    def search(self, query, limit=10, category=None, include_non_authoritative=False):
        if not isinstance(query, str) or not query.strip():
            return []
        needle = query.casefold()
        query_tokens = _tokens(query)
        ranked = []
        for document in self.documents:
            status = document.get("status")
            if not include_non_authoritative and status and (status not in {"canonical", "fixture_verified", "verified"} or document.get("versionUnknown")):
                continue
            if category and document["category"] != category:
                continue
            haystack = document["searchText"]
            score = 0
            if needle == haystack:
                score = 100
            elif needle in haystack:
                score = 60
            else:
                overlap = len(query_tokens & set(document["tokens"]))
                if overlap:
                    score = 10 + overlap
            if score:
                ranked.append((score, document))
        ranked.sort(key=lambda item: (-item[0], item[1]["source"], item[1]["text"]))
        return [{**document, "score": score} for score, document in ranked[:limit]]

    def resolve_item_alias(self, query, category=None):
        """Resolve an exact English/Korean alias to one stable identity."""
        if not isinstance(query, str) or not query:
            raise ValueError("item name is required")
        matches = []
        seen = set()
        for document in self.documents:
            if category and document.get("category") != category:
                continue
            english = document.get("text")
            korean = document.get("korean")
            if query == korean or (isinstance(english, str) and query.casefold() == english.casefold()):
                key = (english, korean, document.get("category"))
                if key not in seen:
                    seen.add(key)
                    matches.append(key)
        if not matches:
            return None
        if len(matches) > 1:
            raise ValueError("item alias is ambiguous")
        english, korean, resolved_category = matches[0]
        return {
            "canonicalId": "%s:%s" % (resolved_category, english),
            "english": english,
            "korean": korean,
            "category": resolved_category,
        }

    def resolve_skill_alias(self, query):
        if not isinstance(query, str) or not query:
            raise ValueError("skill name is required")
        matches = [entry for entry in self.skill_aliases if query == entry["korean"] or query.casefold() == entry["english"].casefold()]
        identities = {(entry["english"], entry["korean"], entry["variantId"]) for entry in matches}
        if not identities:
            return None
        if len(identities) > 1:
            raise ValueError("skill alias is ambiguous")
        entry = matches[0]
        return {key: entry[key] for key in ("english", "korean", "skillId", "gemId", "variantId")}
