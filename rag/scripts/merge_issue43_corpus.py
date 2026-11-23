"""Prepare a version-bound corpus without modifying raw snapshots or ChromaDB."""

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

from rag.src.ingestion.models import Notice

SOURCES = ("incibe", "osi", "banco_espana")
POLICY = "Decisión interna del equipo Avizor: prototipo académico no comercial; no autorización expresa del titular."


def merge_records(paths):
    records = {}
    hashes = {}
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise TypeError("Expected a JSON list")
        for record in data:
            url, digest = record["url"], record["content_hash"]
            # Validate every capture, including duplicates, before choosing one.
            Notice.from_record(
                record,
                today=date.today(),
                synthetic=False,
                approval={
                    "content_hash": digest,
                    "rag_allowed": True,
                    "reference": POLICY,
                    "threat_type": "other",
                },
            )
            if url in records:
                if records[url]["content_hash"] != digest:
                    raise ValueError(
                        "Conflicting versions; review before merging: " + url
                    )
                continue
            if digest in hashes:
                raise ValueError(
                    "Same content at multiple URLs; review canonical source: " + url
                )
            records[url] = record
            hashes[digest] = url
    return records


def prepare(records, labels, *, accept):
    if records.keys() != labels.keys():
        raise ValueError("Labels must cover exactly the merged URLs")
    result = {}
    for url, record in records.items():
        entry = dict(labels[url])
        if entry["content_hash"] != record["content_hash"]:
            raise ValueError("Snapshot changed since classification: " + url)
        entry.update(rag_allowed=accept, reference=POLICY)
        Notice.from_record(
            record,
            today=date.today(),
            synthetic=False,
            approval={**entry, "rag_allowed": True},
        )
        result[url] = entry
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("rag/data/raw"))
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--accept-team-policy", action="store_true")
    args = parser.parse_args()
    paths = [
        args.raw / f"{source}_{suffix}.json"
        for suffix in ("content", "notices")
        for source in SOURCES
    ]
    records = merge_records(paths)
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    result = prepare(records, labels, accept=args.accept_team_policy)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in [
        ("corpus.json", list(records.values())),
        ("approvals.json", result),
    ]:
        (args.output_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    counts = Counter(
        k
        for entry in result.values()
        for k in {entry["threat_type"], *entry.get("secondary_threats", [])}
    )
    print(
        json.dumps(
            {
                "documents": len(records),
                "by_source": dict(Counter(d["source"] for d in records.values())),
                "by_threat": dict(counts),
                "academic_policy_accepted": args.accept_team_policy,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
