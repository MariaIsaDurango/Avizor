"""Offline tests for issue #39."""

import httpx
import pytest

from rag.src.scrapers.poc_official_source import URL, fetch_notice, parse_notice


def test_parse_notice():
    assert parse_notice("<main><h1>Aviso de prueba</h1></main>") == {
        "source": "banco_espana",
        "url": URL,
        "title": "Aviso de prueba",
    }


def test_missing_title():
    with pytest.raises(ValueError):
        parse_notice("<html></html>")


def test_fetch_notice():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<h1>Prueba</h1>"
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert fetch_notice(client)["title"] == "Prueba"


def test_disallowed():
    def handler(request):
        assert request.url.path == "/robots.txt"
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(PermissionError),
    ):
        fetch_notice(client)


def test_unavailable_robots():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ) as client,
        pytest.raises(RuntimeError),
    ):
        fetch_notice(client)


def test_no_redirect():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://example.org"})

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler), follow_redirects=False
        ) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        fetch_notice(client)
