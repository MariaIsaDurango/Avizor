"""ES: Pruebas AJAX sin red. EN: Offline press feed tests."""

from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from rag.src.scrapers.common import FetchError, SafeFetcher
from rag.src.scrapers.policia_scraper import SOURCE
from rag.src.scrapers.run_scrapers import scrape_source

TODAY = date(2026, 11, 17)
AJAX_PATH = "/js/ajax_cargar_noticias.php"


def mock_portal(request, *, payload=None, robots=None):
    """Return synthetic responses, without accessing the real portal."""
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, text=robots or "User-agent: *\nDisallow:")
    if path == "/cookies_set.php":
        assert request.method == "POST"
        return httpx.Response(200, text="1")
    if path == AJAX_PATH:
        assert request.method == "POST"
        return httpx.Response(200, json=payload)
    if path == "/_es/comunicacion_prensa_detalle.php":
        identifier = request.url.params["ID"]
        markup = (
            '<meta property="article:published_time" content="2026-11-10">'
            f"<article><h2>Estafa bancaria {identifier}</h2></article>"
        )
        return httpx.Response(200, text=markup, headers={"content-type": "text/html"})
    return httpx.Response(
        200, text="<html></html>", headers={"content-type": "text/html"}
    )


def test_ajax_pagination_and_unique_notices():
    forms = []

    def handler(request):
        if request.url.path != AJAX_PATH:
            return mock_portal(request)
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        forms.append(form)
        first = len(forms) == 1
        identifier = 123 if first else 124
        markup = (
            f'<a href="comunicacion_prensa_detalle.php?ID={identifier}">Estafa</a>'
            '<a href="https://evil.example/_es/comunicacion_prensa_detalle.php?ID=999">Estafa</a>'
        )
        return mock_portal(
            request,
            payload={
                "contenido": markup,
                "desde": 10,
                "hasta": 20,
                "contador": int(first),
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        records, report = scrape_source(SOURCE, fetcher, today=TODAY, limit=2)
    assert report["target_met"]
    assert len(records) == 2
    assert forms[0] == {
        "cargar_mas": ["si"],
        "desde": [""],
        "hasta": [""],
        "anyo": ["2026"],
        "mes": ["11"],
        "lang": ["es"],
    }
    assert forms[1]["desde"] == ["10"]
    assert forms[1]["hasta"] == ["20"]
    assert all(record.url.startswith("https://www.policia.es/") for record in records)


def test_ajax_month_rollover():
    months = []

    def handler(request):
        if request.url.path == AJAX_PATH:
            form = parse_qs(request.content.decode(), keep_blank_values=True)
            months.append((form["anyo"][0], form["mes"][0]))
            return mock_portal(request, payload={"contenido": "", "contador": 0})
        return mock_portal(request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        records, report = scrape_source(
            SOURCE, fetcher, today=date(2026, 1, 15), max_pages=2
        )
    assert not records
    assert not report["target_met"]
    assert months == [("2026", "1"), ("2025", "12")]


def test_ajax_respects_robots():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return mock_portal(request, robots=f"User-agent: *\nDisallow: {AJAX_PATH}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        _, report = scrape_source(SOURCE, fetcher, today=TODAY)
    assert AJAX_PATH not in calls
    assert report["errors"] == ["robots.txt disallows police news endpoint"]


def test_ajax_without_explicit_consent():
    with (
        httpx.Client(transport=httpx.MockTransport(mock_portal)) as client,
        pytest.raises(FetchError, match="session required"),
    ):
        SafeFetcher(client, delay=0).police_news(2026, 11, "", "")


def test_ajax_invalid_response():
    def handler(request):
        return mock_portal(request, payload=["invalid"])

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        _, report = scrape_source(SOURCE, fetcher, today=TODAY)
    assert not report["target_met"]
    assert report["errors"] == ["Invalid police news response"]


def test_ajax_repeated_cursor_stops():
    def handler(request):
        return mock_portal(
            request,
            payload={
                "contenido": "<p>Sin avisos relevantes</p>",
                "contador": 1,
                "desde": "",
                "hasta": "",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0, accept_police_cookies=True)
        _, report = scrape_source(SOURCE, fetcher, today=TODAY)
    assert report["pages"] == 1
    assert report["errors"] == ["Repeated police pagination cursor"]
