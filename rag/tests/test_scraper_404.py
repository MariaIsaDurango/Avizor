"""Regression tests for recoverable article 404s and fatal access failures."""

from datetime import date

import httpx
import pytest

from rag.src.scrapers.common import (
    POLICE_COOKIES_ENDPOINT,
    POLICE_COOKIES_PAGE,
    POLICE_NEWS_ENDPOINT,
    SafeFetcher,
)
from rag.src.scrapers.incibe_scraper import SOURCE as INCIBE
from rag.src.scrapers.policia_scraper import SOURCE as POLICIA
from rag.src.scrapers.run_scrapers import scrape_source

TODAY = date(2026, 11, 17)
URLS = [f"https://www.incibe.es/ciudadania/avisos/fraude-{n}" for n in range(3)]


def article(number):
    return httpx.Response(
        200,
        headers={"content-type": "text/html"},
        text=(
            "<article><h1>Alerta de fraude digital "
            f'{number}</h1><time datetime="2026-11-10"></time></article>'
        ),
    )


@pytest.mark.parametrize("missing", [0, 1])
def test_article_404_continues(missing):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        number = URLS.index(str(request.url))
        return httpx.Response(404) if number == missing else article(number)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0)
        records, report = scrape_source(
            INCIBE, fetcher, today=TODAY, limit=2, seeds=URLS
        )
        assert not fetcher.blocked_hosts
    assert {record.url for record in records} == set(URLS) - {URLS[missing]}
    assert report["skipped_404"] == [URLS[missing]]
    assert report["rejected"] == 1
    assert report["articles_attempted"] == 3
    assert report["errors"] == []
    assert report["target_met"]


def test_all_articles_404():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            INCIBE, SafeFetcher(client, delay=0), today=TODAY, limit=2, seeds=URLS
        )
    assert not records
    assert report["skipped_404"] == URLS
    assert report["rejected"] == 3
    assert not report["target_met"]


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_fatal_article_status_stops(status):
    requested = []

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        requested.append(str(request.url))
        return httpx.Response(status)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0)
        records, report = scrape_source(
            INCIBE, fetcher, today=TODAY, limit=2, seeds=URLS
        )
        assert INCIBE.host in fetcher.blocked_hosts
    assert requested == URLS[:1]
    assert not records
    assert report["skipped_404"] == []
    assert report["errors"] == [f"HTTP {status}; stopped"]
    assert not report["target_met"]


def test_index_404_is_fatal():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            INCIBE, SafeFetcher(client, delay=0), today=TODAY, limit=2
        )
    assert not records
    assert report["skipped_404"] == []
    assert report["errors"] == ["HTTP 404; stopped"]
    assert not report["target_met"]


@pytest.mark.parametrize("missing", [POLICE_COOKIES_PAGE, POLICE_COOKIES_ENDPOINT])
def test_cookie_404_is_fatal(missing):
    url = "https://www.policia.es/_es/comunicacion_prensa_detalle.php?ID=123"
    requested = []

    def handler(request):
        current = str(request.url)
        requested.append(current)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if current == missing:
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="OK")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        records, report = scrape_source(
            POLICIA, fetcher, today=TODAY, limit=1, seeds=[url]
        )
    assert url not in requested
    assert not records
    assert report["skipped_404"] == []
    assert report["errors"] == ["HTTP 404; stopped"]
    assert not report["target_met"]


def test_police_ajax_404_is_fatal():
    def handler(request):
        current = str(request.url)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if current == POLICE_COOKIES_ENDPOINT:
            return httpx.Response(200, text="1")
        if current == POLICE_NEWS_ENDPOINT:
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="OK")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        records, report = scrape_source(POLICIA, fetcher, today=TODAY, limit=1)
    assert not records
    assert report["skipped_404"] == []
    assert report["errors"] == ["HTTP 404; stopped"]
    assert not report["target_met"]


def test_discovered_article_404_continues():
    def handler(request):
        current = str(request.url)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if current == INCIBE.indexes[0]:
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="".join(f'<a href="{url}">Fraude digital</a>' for url in URLS),
            )
        number = URLS.index(current)
        return httpx.Response(404) if number == 0 else article(number)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            INCIBE, SafeFetcher(client, delay=0), today=TODAY, limit=2
        )
    assert {record.url for record in records} == set(URLS[1:])
    assert report["skipped_404"] == URLS[:1]
    assert report["target_met"]
