"""ES: Ejecución limitada y auditable. EN: Bounded, auditable scraping CLI."""

import argparse
import json
from collections import Counter, deque
from datetime import date
from pathlib import Path

import httpx

from .banco_espana_scraper import SOURCE as BANCO
from .common import (
    FetchError,
    Notice,
    SafeFetcher,
    Source,
    cutoff_date,
    deduplicate,
    discover,
    is_bank_education_index,
    parse_notice,
    relevant_title,
    sha256_text,
)
from .incibe_scraper import SOURCE as INCIBE
from .osi_scraper import SOURCE as OSI
from .policia_scraper import SOURCE as POLICIA
from .policia_scraper import news_batches

SOURCES = {source.name: source for source in (INCIBE, OSI, POLICIA, BANCO)}
ROOT = Path(__file__).resolve().parents[3]


def scrape_source(
    source: Source,
    fetcher: SafeFetcher,
    *,
    limit: int = 10,
    max_pages: int = 20,
    today: date | None = None,
    reuse_reference: str | None = None,
    seeds: list[str] | None = None,
    police_start_month: date | None = None,
    police_end_month: date | None = None,
    existing_notices: list[Notice] | None = None,
) -> tuple[list[Notice], dict]:
    """Return unique recent notices and honest partial-run diagnostics."""
    today = today or date.today()
    queue = deque(source.indexes if seeds is None else [])
    visited_pages: set[str] = set()
    visited_articles: set[str] = set()
    notices = deduplicate(existing_notices or [])
    initial_count = len(notices)
    visited_articles.update(n.url for n in notices)
    previous_urls = set(visited_articles)
    months_scanned: set[str] = set()
    errors: list[str] = []
    rejected = 0
    initial_requests = fetcher.requests

    def fetch_articles(urls: list[str]) -> None:
        nonlocal rejected, notices
        for raw in urls:
            if len(notices) >= limit:
                break
            url = source.article_url(raw)
            if url is None:
                rejected += 1
                continue
            alias_key = url.replace(
                "https://www.incibe.es/index.php/", "https://www.incibe.es/"
            )
            if alias_key in visited_articles:
                continue
            visited_articles.add(alias_key)
            try:
                html = fetcher.get(url, source)
            except FetchError as exc:
                if str(exc) == "Expected HTML":
                    rejected += 1
                    continue
                raise

            record = parse_notice(html, url, source, today, reuse_reference)
            if record is None:
                rejected += 1
                continue
            notices = deduplicate([*notices, record])

    try:
        if initial_count >= limit:
            queue.clear()
        elif seeds is not None:
            fetch_articles(seeds)
        elif source.name == "policia_nacional" and fetcher.accept_police_cookies:
            for key, articles in news_batches(
                source,
                fetcher,
                today,
                max_pages,
                start_month=police_start_month,
                end_month=police_end_month,
            ):
                visited_pages.add(key)
                months_scanned.add(key.split(":", 1)[0])
                fetch_articles(articles)
                if len(notices) >= limit:
                    break
            queue.clear()
        while queue and len(visited_pages) < max_pages and len(notices) < limit:
            page = source.index_url(queue.popleft())
            if page is None or page in visited_pages:
                continue
            visited_pages.add(page)
            articles, pages = discover(fetcher.get(page, source), page, source)
            fetch_articles(articles)
            pending = [p for p in pages if p not in visited_pages]
            if source.name == "banco_espana" and is_bank_education_index(page):
                queue.extendleft(reversed(pending))
            else:
                queue.extend(pending)
    except FetchError as exc:
        errors.append(str(exc))
    report = {
        "source": source.name,
        "publisher": source.publisher,
        "mode": "content" if reuse_reference else "metadata",
        "target": limit,
        "unique_recent": len(notices),
        "content_records": sum(n.text is not None for n in notices),
        "pages": len(visited_pages),
        "articles_attempted": len(visited_articles - previous_urls),
        "rejected": rejected,
        "requests": fetcher.requests - initial_requests,
        "errors": errors,
        "target_met": len(notices) >= limit and not errors,
    }
    if source.name == "policia_nacional":
        report["months_scanned"] = sorted(months_scanned, reverse=True)
        report["previous_unique"] = initial_count
        report["new_unique"] = len(notices) - initial_count
    return notices, report


def parse_month(value: str) -> date:
    """Parse an explicit YYYY-MM argument."""
    try:
        parsed = date.fromisoformat(f"{value}-01")
        if parsed.isoformat()[:7] != value:
            raise ValueError
    except TypeError as exc:
        raise argparse.ArgumentTypeError("Expected YYYY-MM") from exc
    return parsed


def load_police_metadata(path: Path, today: date) -> list[Notice]:
    """Reuse only valid, recent, canonical police metadata (never full texts)."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError("Expected a list in the existing metadata snapshot")
    records = []
    for item in raw:
        notice = Notice(**item)
        if (
            notice.source != POLICIA.name
            or notice.publisher != POLICIA.publisher
            or notice.text is not None
            or notice.content_hash is not None
            or notice.reuse_reference is not None
            or POLICIA.article_url(notice.url) != notice.url
            or notice.metadata_hash
            != sha256_text(f"{notice.title}\n{notice.published_at}")
        ):
            raise ValueError("Existing snapshot is not valid police metadata")
        if cutoff_date(today) <= date.fromisoformat(
            notice.published_at
        ) <= today and relevant_title(notice.title, POLICIA.name):
            records.append(notice)
    return deduplicate(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", *SOURCES], default="all")
    parser.add_argument(
        "--limit", type=int, default=10, choices=range(1, 51), metavar="1..50"
    )
    parser.add_argument(
        "--max-pages", type=int, default=20, choices=range(1, 41), metavar="1..40"
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        help="JSON list of reviewed official article URLs; one source only",
    )
    parser.add_argument(
        "--reuse-reference", help="Documented reuse approval reference; one source only"
    )
    parser.add_argument(
        "--save", action="store_true", help="Save local JSON snapshot (ignored by Git)"
    )
    parser.add_argument(
        "--accept-police-cookies",
        action="store_true",
        help="Accept technical cookies for the official police portal",
    )
    parser.add_argument(
        "--police-start-month",
        type=parse_month,
        metavar="YYYY-MM",
        help="Start police backfill at this month (default: current month)",
    )
    parser.add_argument(
        "--police-end-month",
        type=parse_month,
        metavar="YYYY-MM",
        help="Stop after this month (inclusive; default: 24-month cutoff)",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Preserve and deduplicate existing police metadata with new results",
    )
    args = parser.parse_args()
    today = date.today()
    if args.police_start_month or args.police_end_month or args.merge_existing:
        if (
            args.source != POLICIA.name
            or not args.accept_police_cookies
            or args.seed_file
            or args.reuse_reference is not None
        ):
            parser.error(
                "Police backfill requires police source, cookie consent and metadata mode"
            )
        first = args.police_start_month or today.replace(day=1)
        last = args.police_end_month or cutoff_date(today).replace(day=1)
        if (
            not cutoff_date(today).replace(day=1)
            <= last
            <= first
            <= today.replace(day=1)
        ):
            parser.error("Police month range outside the last 24 months")
    if args.merge_existing and not args.save:
        parser.error("--merge-existing requires --save")
    if args.source == "all" and (args.seed_file or args.reuse_reference):
        parser.error("Seeds and reuse reference require a single source")
    if args.reuse_reference is not None and not args.reuse_reference.strip():
        parser.error("Reuse reference cannot be blank")
    seeds = None
    if args.seed_file:
        seeds = json.loads(args.seed_file.read_text(encoding="utf-8"))
        if not isinstance(seeds, list) or not all(
            isinstance(item, str) for item in seeds
        ):
            parser.error("Seed file must be a JSON list of URLs")
    output = ROOT / "rag" / "data" / "raw" / f"{args.source}_notices.json"
    existing = []
    if args.merge_existing:
        try:
            existing = load_police_metadata(output, today)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            parser.error(f"Cannot merge existing metadata: {exc}")
    records, reports = [], []
    chosen = list(SOURCES.values()) if args.source == "all" else [SOURCES[args.source]]
    with httpx.Client(timeout=httpx.Timeout(20.0), follow_redirects=False) as client:
        fetcher = SafeFetcher(
            client,
            accept_police_cookies=args.accept_police_cookies,
        )
        for source in chosen:
            # Budget is reset per source; host pacing and robots cache are retained.
            fetcher.budget = fetcher.requests + 100
            batch, report = scrape_source(
                source,
                fetcher,
                limit=args.limit,
                max_pages=args.max_pages,
                seeds=seeds,
                reuse_reference=args.reuse_reference,
                police_start_month=args.police_start_month,
                police_end_month=args.police_end_month,
                existing_notices=existing,
            )
            records.extend(batch)
            reports.append(report)
    unique = deduplicate(records)
    counts = Counter(n.source for n in unique)
    for report in reports:
        report["unique_after_global_dedup"] = counts[report["source"]]
        report["target_met"] = (
            report["target_met"] and counts[report["source"]] >= args.limit
        )
    result = {
        "sources": reports,
        "total_before_global_dedup": len(records),
        "total_unique": len(unique),
        "duplicates_removed_globally": len(records) - len(unique),
        "unique_by_source": dict(counts),
        "indexable_content_records": sum(n.text is not None for n in unique),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.save:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([n.to_dict() for n in unique], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(output)
        print(f"Local snapshot: {output}")
    return 0 if all(item["target_met"] for item in reports) else 2


if __name__ == "__main__":
    raise SystemExit(main())
