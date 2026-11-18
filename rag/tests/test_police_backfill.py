"""ES: Recuperación histórica de metadatos. EN: Bounded backfill tests."""

import json
from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from rag.src.scrapers.common import Notice, SafeFetcher, sha256_text
from rag.src.scrapers.policia_scraper import SOURCE
from rag.src.scrapers.run_scrapers import load_police_metadata, scrape_source

TODAY = date(2026, 11, 17)


def notice(identifier=123, published="2026-10-01"):
    title = f"Estafa bancaria {identifier}"
    return Notice(
        source=SOURCE.name,
        publisher=SOURCE.publisher,
        url=f"https://www.policia.es/_es/comunicacion_prensa_detalle.php?ID={identifier}",
        title=title,
        published_at=published,
        scraped_at="2026-11-17T10:00:00Z",
        language="es",
        text=None,
        content_hash=None,
        metadata_hash=sha256_text(f"{title}\n{published}"),
        reuse_reference=None,
    )


def test_backfill_merges_without_refetching_known_url():
    forms = []
    fetched = []

    def handler(request):
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if path == "/cookies_set.php":
            return httpx.Response(200, text="1")
        if path == "/js/ajax_cargar_noticias.php":
            form = parse_qs(request.content.decode())
            forms.append((form["anyo"], form["mes"]))
            return httpx.Response(
                200,
                json={
                    "contenido": (
                        '<a href="comunicacion_prensa_detalle.php?ID=123">Estafa</a>'
                        '<a href="comunicacion_prensa_detalle.php?ID=124">Estafa</a>'
                    ),
                    "contador": 0,
                },
            )
        html = "<html></html>"
        if path == "/_es/comunicacion_prensa_detalle.php":
            identifier = request.url.params["ID"]
            fetched.append(identifier)
            html = (
                '<meta property="article:published_time" content="2026-08-03">'
                "<article><h2>Estafa bancaria 124</h2></article>"
            )
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        records, report = scrape_source(
            SOURCE,
            fetcher,
            today=TODAY,
            limit=2,
            police_start_month=date(2026, 8, 1),
            police_end_month=date(2026, 8, 1),
            existing_notices=[notice()],
        )
    assert forms == [(["2026"], ["8"])]
    assert fetched == ["124"]
    assert len(records) == 2
    assert report["target_met"]
    assert report["previous_unique"] == 1
    assert report["new_unique"] == 1
    assert report["months_scanned"] == ["2026-08"]
    assert report["articles_attempted"] == 1


def test_existing_target_avoids_network():
    def handler(request):
        raise AssertionError(f"Unexpected request: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            SOURCE,
            SafeFetcher(client, delay=0, accept_police_cookies=True),
            today=TODAY,
            limit=1,
            existing_notices=[notice()],
        )
    assert len(records) == 1
    assert report["requests"] == 0
    assert report["target_met"]


def test_load_snapshot_removes_duplicates_and_expired(tmp_path):
    path = tmp_path / "notices.json"
    valid = notice().to_dict()
    expired = notice(124, "2024-11-16").to_dict()
    path.write_text(json.dumps([valid, valid, expired]), encoding="utf-8")
    assert load_police_metadata(path, TODAY) == [notice()]


def test_load_snapshot_rejects_modified_hash(tmp_path):
    path = tmp_path / "notices.json"
    record = notice().to_dict()
    record["title"] = "Contenido manipulado"
    path.write_text(json.dumps([record]), encoding="utf-8")
    with pytest.raises(ValueError, match="not valid police metadata"):
        load_police_metadata(path, TODAY)
