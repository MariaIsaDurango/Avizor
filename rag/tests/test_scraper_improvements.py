"""ES: Mejoras de scraping. EN: Scraping regression tests."""

import httpx
import pytest

from rag.src.scrapers.common import FRAUD, FetchError, SafeFetcher
from rag.src.scrapers.policia_scraper import SOURCE


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Un Bizum para pagar en la cafetería", False),
        ("Estafas por Bizum", True),
        ("Tómate un tiempo antes de hacer click", True),
    ],
)
def test_fraud_relevance(title, expected):
    assert bool(FRAUD.search(title)) == expected


@pytest.mark.parametrize(
    "accepted",
    [True, False],
)
def test_police_cookie_session(accepted):
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path))
        path = request.url.path

        if path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nDisallow:",
            )

        if path == "/_es/cookies.php":
            return httpx.Response(
                200,
                text="<html>Cookies</html>",
                headers={"content-type": "text/html"},
            )

        if path == "/cookies_set.php":
            assert request.method == "POST"
            return httpx.Response(
                200,
                text="1" if accepted else "0",
            )

        return httpx.Response(
            200,
            text="<html><title>Noticias</title></html>",
            headers={"content-type": "text/html"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
    ) as client:
        fetcher = SafeFetcher(
            client,
            delay=0,
            accept_police_cookies=True,
        )

        url = SOURCE.index_url(SOURCE.indexes[0])
        assert url is not None

        if accepted:
            assert "Noticias" in fetcher.get(url, SOURCE)
            assert "Noticias" in fetcher.get(url, SOURCE)
            assert fetcher.police_cookies_ready
            assert calls.count(("POST", "/cookies_set.php")) == 1
        else:
            with pytest.raises(FetchError, match="not confirmed"):
                fetcher.get(url, SOURCE)

            assert not fetcher.police_cookies_ready


def test_police_cookie_endpoint_blocked():
    def handler(request):
        assert request.url.path == "/robots.txt"

        return httpx.Response(
            200,
            text="User-agent: *\nDisallow: /cookies_set.php",
        )

    with (
        httpx.Client(
            transport=httpx.MockTransport(handler),
        ) as client,
        pytest.raises(FetchError, match="disallows cookie endpoint"),
    ):
        fetcher = SafeFetcher(
            client,
            delay=0,
            accept_police_cookies=True,
        )

        url = SOURCE.index_url(SOURCE.indexes[0])
        assert url is not None
        fetcher.get(url, SOURCE)
