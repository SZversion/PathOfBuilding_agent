import json
import pathlib
import re
import sys


def tokens(value):
    return sorted(set(re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)))


def build(root, output):
    root = pathlib.Path(root)
    documents = []
    for path in sorted((root / "rules").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("rules") or data.get("validation") or []
        for record in records:
            text = record.get("statement") or record.get("finding") or record.get("id", "")
            documents.append({"text": text, "korean": "", "category": record.get("category", "validation"), "source": path.as_posix(), "terms": record.get("terms", [])})
    aliases = json.loads((root / "aliases/ko/items-3.29.json").read_text(encoding="utf-8"))
    for record in aliases["entries"]:
        documents.append({"text": record["english"], "korean": record["korean"], "category": "item." + record["category"], "source": "agent/knowledge/aliases/ko/items-3.29.json", "terms": []})
    for document in documents:
        text = " ".join([document["text"], document["korean"], *document["terms"]])
        document["searchText"] = text.casefold()
        document["tokens"] = tokens(text)
        del document["terms"]
    payload = {"schemaVersion": 1, "game": "poe1", "patch": "3.29", "documents": sorted(documents, key=lambda item: (item["source"], item["text"]))}
    destination = pathlib.Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"indexed {len(documents)} documents")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_knowledge_index.py KNOWLEDGE_DIR OUTPUT_FILE")
    build(sys.argv[1], sys.argv[2])
