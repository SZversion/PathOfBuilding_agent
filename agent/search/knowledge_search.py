import json
import re


def _tokens(value):
    return set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE))


class KnowledgeSearch:
    def __init__(self, index_path):
        with open(index_path, encoding="utf-8") as stream:
            self.documents = json.load(stream)["documents"]

    def search(self, query, limit=10, category=None):
        if not isinstance(query, str) or not query.strip():
            return []
        needle = query.casefold()
        query_tokens = _tokens(query)
        ranked = []
        for document in self.documents:
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
