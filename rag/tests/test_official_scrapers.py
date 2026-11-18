"""ES: Pruebas offline de adaptadores. EN: Offline adapter tests."""

from dataclasses import replace
from datetime import date

import httpx
import pytest

from rag.src.scrapers.banco_espana_scraper import SOURCE as BANCO
from rag.src.scrapers.common import (
    FetchError,
    RobotsPolicy,
    SafeFetcher,
    cutoff_date,
    deduplicate,
    discover,
    parse_date,
    parse_notice,
    sha256_text,
)
from rag.src.scrapers.incibe_scraper import SOURCE as INCIBE
from rag.src.scrapers.osi_scraper import SOURCE as OSI
from rag.src.scrapers.policia_scraper import SOURCE as POLICIA
from rag.src.scrapers.run_scrapers import scrape_source

TODAY = date(2026, 11, 17)
URLS = [
    "https://www.incibe.es/ciudadania/avisos/alerta-ficticia",
    "https://www.incibe.es/ciudadania/blog/alerta-ficticia",
    "https://www.policia.es/_es/comunicacion_prensa_detalle.php?ID=123",
    "https://clientebancario.bde.es/pcb/es/blog/alerta-ficticia.html",
]
SOURCES = [INCIBE, OSI, POLICIA, BANCO]
BODY = "Contenido sintético de prueba sobre la prevención del fraude. " * 3


def html(title="Alerta de fraude digital", published="2026-11-10", body=BODY):
    return (
        f'<html><head><meta property="article:published_time" content="{published}">'
        f"</head><body><main><article><h1>{title}</h1>"
        f'<div class="field--name-body" itemprop="articleBody"><p>{body}</p>'
        "<script>NO_INDEXAR</script><nav>MENÚ</nav></div></article></main></body></html>"
    )


@pytest.mark.parametrize("source,url", list(zip(SOURCES, URLS, strict=True)))
def test_adapter_metadata(source, url):
    record = parse_notice(html(), url, source, TODAY)
    assert record.source == source.name
    assert record.published_at == "2026-11-10"
    assert record.url == url
    assert record.text is None
    assert record.content_hash is None
    assert record.metadata_hash.startswith("sha256:")


@pytest.mark.parametrize("source,url", list(zip(SOURCES, URLS, strict=True)))
def test_adapter_authorized_body(source, url):
    record = parse_notice(html(), url, source, TODAY, "synthetic fixture approval")
    assert record.text
    assert record.content_hash == sha256_text(record.text)
    assert "NO_INDEXAR" not in record.text
    assert "MENÚ" not in record.text


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-11-10T12:00:00Z", date(2026, 11, 10)),
        ("10/11/2026", date(2026, 11, 10)),
        ("10/11/26", date(2026, 11, 10)),
        ("10 de noviembre de 2026", date(2026, 11, 10)),
        ("31/02/2026", None),
        ("sin fecha", None),
    ],
)
def test_publication_date(raw, expected):
    assert parse_date(raw) == expected


@pytest.mark.parametrize("published", ["", "2024-11-16", "2026-11-18"])
def test_reject_missing_old_future(published):
    assert parse_notice(html(published=published), URLS[0], INCIBE, TODAY) is None


def test_plain_date_near_heading():
    text = "<main><h1>Alerta de fraude digital</h1><p>02/01/2025</p></main>"
    record = parse_notice(text, URLS[3], BANCO, TODAY)
    assert record.published_at == "2025-01-02"


def test_cutoff_leap_day():
    assert cutoff_date(date(2024, 2, 29)) == date(2022, 2, 28)


def test_filter_irrelevant_title():
    assert (
        parse_notice(html(title="Noticias de deporte"), URLS[3], BANCO, TODAY) is None
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/ciudadania/avisos/fraude",
        "https://www.incibe.es.evil.example/ciudadania/avisos/fraude",
        "https://evil.example@www.incibe.es/ciudadania/avisos/fraude",
        "http://www.incibe.es/ciudadania/avisos/fraude",
        "https://www.incibe.es:444/ciudadania/avisos/fraude",
        "https://www.incibe.es/ciudadania/avisos/%2e%2e%2fsecret",
        "https://www.incibe.es/ciudadania/avisos/notice.pdf",
    ],
)
def test_allowlist_rejects_unapproved_urls(url):
    assert INCIBE.article_url(url) is None


def test_canonicalization():
    assert BANCO.article_url(URLS[3] + "?utm_source=example#top") == URLS[3]
    assert POLICIA.article_url(URLS[2] + "&idiomaActual=es") == URLS[2]
    assert POLICIA.article_url(URLS[2] + "&ID=456") is None


def test_discovery_and_pagination():
    index = INCIBE.indexes[0]
    links, pages = discover(
        '<a href="/ciudadania/avisos/alerta-ficticia">Aviso</a>'
        '<a href="/ciudadania/avisos/alerta-ficticia?utm_source=x">Aviso</a>'
        '<a href="?page=1">Siguiente</a>'
        '<a href="https://evil.example/ciudadania/avisos/falso">Fraude</a>',
        index,
        INCIBE,
    )
    assert links == [URLS[0]]
    assert pages == [index + "?page=1"]


def test_banco_blog_pagination_is_not_article():
    url = "https://clientebancario.bde.es/pcb/es/blog/index2.html?blog=%2Fwebcb%2FBlog"
    assert BANCO.article_url(url) is None
    assert BANCO.index_url(url) == url


def test_duplicate_hash_and_updated_url():
    original = parse_notice(html(), URLS[0], INCIBE, TODAY, "fixture")
    copy = replace(original, url=URLS[1], source="osi")
    update = replace(
        original,
        text="Nuevo contenido",
        content_hash=sha256_text("Nuevo contenido"),
        scraped_at="9999-01-01T00:00:00Z",
    )
    assert len(deduplicate([original, copy])) == 1
    assert deduplicate([original, update]) == [update]
    assert sha256_text("test   normalizado") == sha256_text("test normalizado")


def test_incibe_aliases_and_metadata_duplicates():
    original = parse_notice(html(), URLS[0], INCIBE, TODAY)
    alias = replace(
        original, url=URLS[0].replace("/ciudadania/", "/index.php/ciudadania/")
    )
    copy = replace(original, source="osi", url=URLS[1])
    assert len(deduplicate([original, alias, copy])) == 1


def test_robots_specific_group_and_wildcards():
    policy = RobotsPolicy(
        "User-agent: *\nDisallow: /\nUser-agent: AvizorResearch\nDisallow: /ciudadania/*/private$\nAllow: /ciudadania/avisos/public\nCrawl-delay: 3"
    )
    assert policy.can_fetch(URLS[0])
    assert not policy.can_fetch("https://www.incibe.es/ciudadania/avisos/private")
    assert policy.delay == 3


def test_robots_longest_rule():
    policy = RobotsPolicy("User-agent: *\nDisallow: /\nAllow: /ciudadania/avisos/")
    assert policy.can_fetch(URLS[0])
    assert not policy.can_fetch(URLS[1])


def test_robots_blocked_before_article_request():
    requests = []

    def handler(request):
        requests.append(request.url.path)
        return httpx.Response(200, text="User-agent: *\nDisallow: /")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0)
        with pytest.raises(FetchError, match="disallows"):
            fetcher.get(URLS[0], INCIBE)
    assert requests == ["/robots.txt"]


@pytest.mark.parametrize("status", [401, 403, 429, 503, 302])
def test_stop_without_redirect(status):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        return httpx.Response(status, headers={"location": "https://evil.example"})

    with httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        fetcher = SafeFetcher(client, delay=0)
        with pytest.raises(FetchError, match=f"HTTP {status}"):
            fetcher.get(URLS[0], INCIBE)
    assert len(requests) == 2
    assert not any("evil.example" in url for url in requests)


def test_rate_limit_pauses_shared_host():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        return httpx.Response(429)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = SafeFetcher(client, delay=0)
        with pytest.raises(FetchError, match="HTTP 429"):
            fetcher.get(URLS[0], INCIBE)
        with pytest.raises(FetchError, match="paused"):
            fetcher.get(URLS[1], OSI)
        assert fetcher.requests == 2


@pytest.mark.parametrize("source,url", list(zip(SOURCES, URLS, strict=True)))
def test_ten_recent_notices_and_deduplication(source, url):
    index = source.indexes[0]
    urls = [
        url.replace("123", str(100 + i))
        if source == POLICIA
        else url.replace("alerta-ficticia", f"alerta-ficticia-{i}")
        for i in range(10)
    ]

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if str(request.url) == index:
            links = "".join(
                f'<a href="{link}">Alerta de fraude digital {i}</a>' * 2
                for i, link in enumerate(urls)
            )
            return httpx.Response(
                200, text=links, headers={"content-type": "text/html"}
            )
        identifier = urls.index(str(request.url))
        return httpx.Response(
            200,
            text=html(
                title=f"Alerta de fraude digital {identifier}",
                body=BODY + str(identifier),
            ),
            headers={"content-type": "text/html"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            source,
            SafeFetcher(client, delay=0),
            today=TODAY,
            reuse_reference="synthetic fixture",
        )
    assert len(records) == 10
    assert report["target_met"]
    assert report["articles_attempted"] == 10
    assert report["content_records"] == 10
    assert len({record.content_hash for record in records}) == 10


def test_partial_result_not_success():
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503))
    ) as client:
        records, report = scrape_source(
            INCIBE, SafeFetcher(client, delay=0), today=TODAY
        )
    assert records == []
    assert report["target_met"] is False
    assert report["errors"]
