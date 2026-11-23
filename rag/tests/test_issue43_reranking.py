"""Contextual promotion never adds candidates or overrides source validation."""

from datetime import date

import pytest

from rag.src.agent.reranking import rerank, topics
from rag.src.agent.retriever import RetrievedNotice


def hit(title, distance, entity="", chunk="a"):
    return RetrievedNotice(
        chunk,
        "fixture",
        "incibe",
        "https://example.invalid/test",
        title,
        date(2026, 1, 1),
        distance,
        True,
        entity,
    )


def test_bank_promoted_from_second_position():
    social = hit("Seguridad Social", 0.1282)
    bank = hit("Suplantación de entidades bancarias", 0.129)
    assert rerank("SMS de mi banco", [social, bank]) == [bank, social]
    assert bank.distance == 0.129


def test_entities_metadata_used():
    generic = hit("Aviso", 0.13)
    specific = hit("Campaña", 0.135, "Entidades bancarias")
    assert rerank("Cuenta de mi banco", [generic, specific])[0] == specific


def test_no_large_distance_override():
    near = hit("Aviso", 0.1)
    far = hit("Banco", 0.14)
    assert rerank("Banco", [far, near]) == [near, far]


@pytest.mark.parametrize("text", ["Hola", "bancal", "publicidad no solicitada"])
def test_no_match_keeps_order(text):
    a, b = hit("Aviso", 0.1), hit("Banco", 0.11)
    assert rerank(text, [b, a]) == [a, b]


def test_accents_and_word_boundaries():
    assert topics("SEGURIDAD SOCIAL y paquetería") == {"social_security", "parcel"}
    assert not topics("bancal")


def test_empty_and_limit():
    assert rerank("Banco", []) == []
    hits = [hit("Banco", 0.1 + i / 100, chunk=str(i)) for i in range(8)]
    assert rerank("Banco", hits) == hits[:5]
