"""Offline snapshot ingestion, independent of scraper and backend imports."""

import argparse
import json
import os
from datetime import UTC, date, datetime, time
from pathlib import Path

from dotenv import dotenv_values

from rag.src.vector_store.chroma_store import ChromaStore
from rag.src.vector_store.embeddings import E5Embedder

from .chunker import TokenChunker
from .models import Notice

ROOT = Path(__file__).resolve().parents[3]
DEMO_PATH = ROOT / "rag/data/processed/issue41_demo_chroma"
OFFICIAL_PATH = ROOT / "rag/chroma_db"
SAMPLE = ROOT / "rag/data/samples/issue41_synthetic.json"


def resolve_official_path() -> Path:
    """Resolve CHROMA_PATH from the environment or root .env, never the demo."""
    configured = os.environ.get("CHROMA_PATH")
    if configured is None:
        configured = dotenv_values(ROOT / ".env", interpolate=False).get("CHROMA_PATH")
    if configured is None:
        path = OFFICIAL_PATH
    else:
        if not configured.strip():
            raise ValueError("CHROMA_PATH must not be empty")
        path = ROOT / Path(configured).expanduser()
    path = path.resolve()
    demo = DEMO_PATH.resolve()
    if path.is_relative_to(demo) or demo.is_relative_to(path):
        raise ValueError("CHROMA_PATH must be separate from the synthetic database")
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_notices(paths, *, synthetic, approvals, today):
    """Validate all inputs before any write; no partial load on bad permission/hash."""
    by_url = {}
    for path in paths:
        raw = read_json(path)
        if not isinstance(raw, list):
            raise TypeError("Expected JSON list")
        for record in raw:
            if synthetic:
                record = dict(
                    record,
                    published_at=today.isoformat(),
                    scraped_at=datetime.combine(
                        today, time.min, tzinfo=UTC
                    ).isoformat(),
                )
            notice = Notice.from_record(
                record,
                today=today,
                synthetic=synthetic,
                approval=approvals.get(record["url"]),
            )
            previous = by_url.get(notice.url)
            if previous and previous.content_hash != notice.content_hash:
                raise ValueError("Conflicting versions of the same URL in input")
            by_url[notice.url] = notice
    return list(by_url.values())


def ingest(notices, chunker, embedder, store):
    report = {
        "inserted": 0,
        "updated": 0,
        "duplicate": 0,
        "chunks_written": 0,
        "minimum_tokens": None,
        "maximum_tokens": 0,
        "maximum_e5_input": 0,
    }
    for notice in notices:
        chunks = chunker.split(notice.text)
        vectors = embedder.encode([chunk.text for chunk in chunks])
        status, count = store.replace(notice, chunks, vectors)
        report[status] += 1
        report["chunks_written"] += count
        sizes = [chunk.token_count for chunk in chunks]
        minimum = min(sizes)
        old_min = report["minimum_tokens"]
        report["minimum_tokens"] = minimum if old_min is None else min(old_min, minimum)
        report["maximum_tokens"] = max(report["maximum_tokens"], max(sizes))
        report["maximum_e5_input"] = max(
            report["maximum_e5_input"], max(c.input_token_count for c in chunks)
        )
    report["stored_chunks"] = store.collection.count()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--input", type=Path, action="append")
    parser.add_argument(
        "--approvals",
        type=Path,
        help="Local, reviewed RAG permissions by exact URL/hash",
    )
    parser.add_argument(
        "--revision", default="main", help="Cached Hugging Face revision"
    )
    parser.add_argument("--query", help="Synthetic demo query only; never user data")
    args = parser.parse_args()
    if args.synthetic:
        if args.approvals:
            parser.error("Synthetic mode does not accept approvals")
        paths = args.input or [SAMPLE]
        approvals = {}
        db_path = DEMO_PATH
    else:
        if not args.input or not args.approvals or args.query:
            parser.error(
                "Official mode requires --input and --approvals; query is demo-only"
            )
        paths = args.input
        approvals = read_json(args.approvals)
        try:
            db_path = resolve_official_path()
        except ValueError as exc:
            parser.error(str(exc))
    notices = load_notices(
        paths, synthetic=args.synthetic, approvals=approvals, today=date.today()
    )
    embedder = E5Embedder(args.revision)
    chunker = TokenChunker(embedder.tokenizer)
    store = ChromaStore(db_path, revision=embedder.revision, synthetic=args.synthetic)
    report = ingest(notices, chunker, embedder, store)
    report.update(
        {
            "mode": "synthetic" if args.synthetic else "official",
            "database": str(db_path),
            "model_revision": embedder.revision,
        }
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.query:
        result = store.query(embedder.encode([args.query], query=True)[0])
        for meta, distance in zip(
            result["metadatas"][0], result["distances"][0], strict=True
        ):
            print(f"SYNTHETIC | distance={distance:.4f} | {meta['title']}")


if __name__ == "__main__":
    main()
