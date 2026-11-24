"""Tests de extracción de enlaces del texto anonimizado (#151).
Link extraction tests from the anonymized text (#151).
"""

import pytest

from app.services.detection.url_extract import MAX_URLS, extract_urls, merge_urls


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "BBVA: cuenta bloqueada. Verifique en https://bbva-seguro.top/login.",
            ["https://bbva-seguro.top/login"],
        ),
        ("Paga en correos-envio.top/pago ya", ["https://correos-envio.top/pago"]),
        ("Visita www.premio-gratis.es!", ["https://www.premio-gratis.es/"]),
        ("(ver https://a.com/x)", ["https://a.com/x"]),
        (
            "Mira https://es.wikipedia.org/wiki/A_(b).",
            ["https://es.wikipedia.org/wiki/A_(b)"],
        ),
        ("HTTPS://BBVA-Seguro.TOP/Login", ["https://bbva-seguro.top/Login"]),
    ],
)
def test_finds_links(text, expected):
    assert extract_urls(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "Hola mamá, llego a las 8 para cenar.",
        "Escribe a [EMAIL] o llama al [PHONE]",
        "Sr. García, la reunión es a las 5.30 en la sala 2.1",
        "Versión v1.com y 3.es no son enlaces",
        "Mensaje cortado https://s",
        "",
    ],
)
def test_ignores_text_without_links(text):
    assert extract_urls(text) == []


def test_stops_at_anonymization_placeholder():
    # ES: El marcador nunca forma parte del enlace. El enlace se corta en "[" y queda
    #     "?id=" vacío: es lo esperado, el dominio sigue siendo válido y se revisa.
    # EN: The placeholder is never part of the link. The link stops at "[" and keeps
    #     an empty "?id=": expected, since the domain is still valid and gets checked.
    assert extract_urls("Entra https://bbva.es/app?id=[PHONE]") == [
        "https://bbva.es/app?id="
    ]


def test_no_duplicates_and_limit():
    text = " ".join(f"https://d{i}.com/x https://d{i}.com/x" for i in range(15))
    urls = extract_urls(text)
    assert len(urls) == MAX_URLS
    assert len(set(urls)) == MAX_URLS


def test_merge_keeps_given_first_and_dedupes():
    given = ["https://bbva-seguro.top/login"]
    text = "Entra en https://bbva-seguro.top/login o en amazon-pago.shop/x"
    assert merge_urls(given, text) == [
        "https://bbva-seguro.top/login",
        "https://amazon-pago.shop/x",
    ]
