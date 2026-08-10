"""Import exact Korean PoE1 item aliases from the translated PoB CSV files."""
import csv
import hashlib
import json
import pathlib
import sys

SOURCES = (
    ("unique", "고유.csv"),
    ("base_type", "기본유형.csv"),
    ("special_flask", "POE1_특수_플라스크.csv"),
    ("corrupted_unique", "POE1_삿된_고유_아이템_번호.csv"),
)


def main(source_dir: str, output_file: str) -> None:
    root = pathlib.Path(source_dir)
    entries = {}
    metadata = []
    for category, filename in SOURCES:
        path = root / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        count = 0
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream):
                if len(row) < 2 or row[0] == "":
                    continue
                english, korean = row[0], row[1]
                previous = entries.get(english)
                if previous and previous["korean"] != korean:
                    raise ValueError(f"conflicting translation for {english!r}")
                entries[english] = {"english": english, "korean": korean, "category": category}
                count += 1
        metadata.append({"file": filename, "category": category, "sha256": digest, "rows": count})

    payload = {
        "schemaVersion": 1,
        "game": "PoE1",
        "patchRange": "3.29",
        "source": "POE1 Korean PoB (2026.08.07)",
        "exactStringPolicy": "No trimming, spacing, punctuation, or spelling normalization.",
        "sources": metadata,
        "entries": [entries[key] for key in sorted(entries)],
    }
    destination = pathlib.Path(output_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(entries)} aliases to {destination}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: import_korean_item_aliases.py SOURCE_DIR OUTPUT_FILE")
    main(sys.argv[1], sys.argv[2])
