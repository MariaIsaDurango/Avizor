import time

import pytest

from src.ner.anonymizer import AnonymizationResult, NER_MODEL_VERSION, anonymize

# Detect at collection time whether the spaCy model is available.
try:
    from src.ner.anonymizer import _load_spacy
    _load_spacy()
    _HAS_MODEL = True
except (ImportError, OSError):
    _HAS_MODEL = False

requires_model = pytest.mark.skipif(not _HAS_MODEL, reason="es_core_news_sm not installed")

CPU_LATENCY_TARGET_MS = 200


# ---------------------------------------------------------------------------
# Regex tests — no spaCy model required, always run in CI
# ---------------------------------------------------------------------------

def test_email_censored():
    r = anonymize("Escríbeme a juan.garcia@gmail.com", use_ner=False)
    assert "[EMAIL]" in r.text
    assert "@gmail.com" not in r.text
    assert "EMAIL" in r.entities_found


def test_phone_censored():
    r = anonymize("Llama al 612 345 678 cuando puedas.", use_ner=False)
    assert "[PHONE]" in r.text
    assert "612" not in r.text
    assert "PHONE" in r.entities_found


def test_iban_censored():
    r = anonymize("Transfiere a ES91 2100 0418 4502 0005 1332", use_ner=False)
    assert "[IBAN]" in r.text
    assert "ES91" not in r.text
    assert "IBAN" in r.entities_found


def test_card_censored():
    r = anonymize("Paga con la tarjeta 4111 1111 1111 1111", use_ner=False)
    assert "[CARD]" in r.text
    assert "CARD" in r.entities_found


def test_dni_censored():
    r = anonymize("Mi DNI es 12345678Z, envíame el recibo.", use_ner=False)
    assert "[ID_NUMBER]" in r.text
    assert "12345678Z" not in r.text
    assert "ID_NUMBER" in r.entities_found


def test_nie_censored():
    r = anonymize("Número de NIE: X1234567L", use_ner=False)
    assert "[ID_NUMBER]" in r.text
    assert "ID_NUMBER" in r.entities_found


def test_url_kept():
    # URLs are intentionally NOT anonymized — the domain is a phishing signal.
    text = "Haz clic aquí: https://phishing.example.com/login"
    r = anonymize(text, use_ner=False)
    assert "phishing.example.com" in r.text
    assert "[URL]" not in r.text
    assert "URL" not in r.entities_found


def test_multiple_entities_in_one_text():
    r = anonymize(
        "Llama al 612 345 678 o escribe a user@example.com",
        use_ner=False,
    )
    assert "[PHONE]" in r.text
    assert "[EMAIL]" in r.text
    assert "PHONE" in r.entities_found
    assert "EMAIL" in r.entities_found


def test_lowercase_entities():
    r = anonymize(
        "IBAN es91 2100 0418 4502 0005 1332, DNI 12345678z, NIE x1234567l",
        use_ner=False,
    )
    assert "[IBAN]" in r.text
    assert "es91" not in r.text
    assert "[ID_NUMBER]" in r.text
    assert "12345678z" not in r.text
    assert "x1234567l" not in r.text


def test_clean_text_unchanged():
    text = "Hola, ¿cómo estás? Ha llegado un paquete para ti."
    r = anonymize(text, use_ner=False)
    assert r.text == text
    assert r.entities_found == []


def test_returns_anonymization_result_type():
    assert isinstance(anonymize("test", use_ner=False), AnonymizationResult)


def test_ner_model_version_is_nonempty_string():
    assert isinstance(NER_MODEL_VERSION, str) and NER_MODEL_VERSION


# ---------------------------------------------------------------------------
# NER tests — skipped automatically in CI if model is not installed
# ---------------------------------------------------------------------------

@requires_model
def test_name_censored():
    r = anonymize("Hola, me llamo Juan García y quiero hacer una transferencia.")
    assert "[NAME]" in r.text
    assert "NAME" in r.entities_found


@requires_model
def test_address_censored():
    r = anonymize("Vivo en Madrid y necesito que me envíes el paquete.")
    assert "[ADDRESS]" in r.text
    assert "ADDRESS" in r.entities_found


@requires_model
def test_cpu_latency_under_200ms():
    text = "Hola, me llamo Juan García. Mi IBAN es ES91 2100 0418 4502 0005 1332 y mi email es juan@banco.es."
    # Warm-up
    anonymize(text)
    timings = []
    for _ in range(10):
        t0 = time.perf_counter()
        anonymize(text)
        timings.append((time.perf_counter() - t0) * 1000)
    median_ms = sorted(timings)[len(timings) // 2]
    assert median_ms < CPU_LATENCY_TARGET_MS, (
        f"Latencia mediana {median_ms:.1f} ms supera el objetivo de {CPU_LATENCY_TARGET_MS} ms"
    )
