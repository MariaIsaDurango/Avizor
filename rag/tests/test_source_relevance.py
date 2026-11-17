"""ES: Relevancia por fuente. EN: Source-specific relevance tests."""

from datetime import date

import httpx
import pytest

from rag.src.scrapers.banco_espana_scraper import SOURCE as BANCO
from rag.src.scrapers.common import SafeFetcher, discover, relevant_title
from rag.src.scrapers.run_scrapers import scrape_source


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        (
            "Estafa a clientes de bancos por suplantación del departamento antifraude",
            True,
        ),
        ("Fraude masivo a la Seguridad Social", False),
        ("Ciberataque a datos sanitarios", False),
        ("Blanqueo de dinero de estafas informáticas", False),
        ("Uso fraudulento de documentación para viajar", False),
        ("Fraude carrusel a la Hacienda Pública", False),
        ("Documentación fraudulenta para acceder a España", False),
        ("Estafa por parameter tampering", False),
        ("Comisión masiva de estafas informáticas", True),
        ("Estafas a mayores para apropiarse de viviendas", False),
        ("Smishing mediante un SMS falso", True),
        ("Estafa por WhatsApp a personas mayores", True),
    ],
)
def test_police_relevance(title, expected):
    assert relevant_title(title, "policia_nacional") is expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Un Bizum para pagar en la cafetería", False),
        ("Estafas por Bizum", True),
        ("TrickMo: malware que amenaza tus finanzas", True),
        ("Alertas falsas del Banco de España", True),
    ],
)
def test_bank_relevance(title, expected):
    assert relevant_title(title, "banco_espana") is expected


def test_bank_category_pagination():
    index = BANCO.indexes[0]
    assert BANCO.index_url(index) == index
    html = (
        '<a href="index2.html?blog=/webcb/Blog/EducacionFinanciera">2</a>'
        '<a href="index46.html?blog=/webcb/Blog/EducacionFinanciera">46</a>'
        '<a href="index3.html?blog=/webcb/Blog">3</a>'
    )
    articles, pages = discover(html, index, BANCO)
    assert not articles
    assert pages == [
        (
            "https://clientebancario.bde.es/pcb/es/blog/index2.html"
            "?blog=%2Fwebcb%2FBlog%2FEducacionFinanciera"
        )
    ]


def test_bank_category_next_has_priority():
    requested = []

    def handler(request):
        requested.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow:")
        if request.url.path == "/pcb/es/blog/":
            text = '<a href="index2.html?blog=/webcb/Blog/EducacionFinanciera">2</a>'
        elif request.url.path == "/pcb/es/blog/index2.html":
            text = '<a href="fraude.html">Fraude digital</a>'
        elif request.url.path == "/pcb/es/blog/fraude.html":
            text = "<article><h1>Fraude digital</h1><p>10/11/2026</p></article>"
        else:
            raise AssertionError(f"Unexpected request: {request.url}")
        return httpx.Response(200, text=text, headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        records, report = scrape_source(
            BANCO,
            SafeFetcher(client, delay=0),
            today=date(2026, 11, 17),
            limit=1,
        )
    assert report["target_met"]
    assert len(records) == 1
    assert requested == [
        "/robots.txt",
        "/pcb/es/blog/",
        "/pcb/es/blog/index2.html",
        "/pcb/es/blog/fraude.html",
    ]
