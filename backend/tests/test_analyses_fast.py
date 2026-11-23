"""Tests de POST /analyses por la vía rápida (necesitan PostgreSQL).
POST /analyses fast path tests (need PostgreSQL).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.privacy import hash_indicator
from app.models.alert import Alert
from app.models.analysis import Analysis, TempContent
from app.models.indicator import Indicator
from app.schemas.enums import IndicatorType
from app.schemas.verdict import Verdict

ANALYSES = "/api/v1/analyses"
SPAM_PHONE = "+34612345612"  # ES/EN: fake number


def sms_request(device_id, text, urls=(), applied=True):
    return {
        "device_id": str(device_id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-04T13:12:05Z",
        "sender": {"type": "phone", "value": SPAM_PHONE},
        "content": {
            "text": text,
            "urls": list(urls),
            "language": "es",
            "anonymization": {
                "applied": applied,
                "ner_model_version": "ner-es-mobile-0.3.1",
                "redacted_entities": ["IBAN"],
            },
        },
        "app": {"version": "0.4.0", "android_api": 34},
    }


def phone_lookup(device_id, number=SPAM_PHONE):
    return {
        "device_id": str(device_id),
        "channel": "call",
        "origin": "manual",
        "input_type": "phone_number",
        "received_at": "2026-11-04T13:41:00Z",
        "sender": {"type": "phone", "value": number},
    }


PHISHING = "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique en el enlace."
PHISHING_URL = "https://bbva-seguro.top/login"
SPAM = "Has ganado un premio. Oferta exclusiva solo hoy."
FAMILY = "Hola mamá, llego a las 8 para cenar."


@pytest.fixture
def red_response(api_client, consented_senior):
    body = sms_request(consented_senior.device.id, PHISHING, [PHISHING_URL])
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 200
    return response


# ---------- Verdict ----------


def test_phishing_sms_is_red_verdict(red_response):
    verdict = Verdict.model_validate(red_response.json())
    assert verdict.risk_level == "red"
    assert verdict.action == "block_and_alert"
    assert verdict.phase == "fast"
    assert verdict.final is True


def test_verdict_has_no_free_text(red_response):
    """ES: La app Sénior solo recibe la plantilla. EN: The app only gets the template."""
    assert set(red_response.json()) == set(Verdict.model_fields)


def test_family_message_is_green_and_stores_nothing(
    api_client, db_session, consented_senior
):
    body = sms_request(consented_senior.device.id, FAMILY)
    body["sender"] = {"type": "phone", "value": "+34699000111"}
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.json()["risk_level"] == "green"
    analysis_id = response.json()["analysis_id"]
    assert db_session.get(TempContent, analysis_id) is None
    assert (
        db_session.scalar(select(Alert).where(Alert.analysis_id == analysis_id)) is None
    )


# ---------- Privacidad / Privacy ----------


def test_analysis_row_stores_hmac_not_phone(db_session, red_response):
    analysis = db_session.get(Analysis, red_response.json()["analysis_id"])
    assert analysis.sender_hash == hash_indicator(IndicatorType.PHONE, SPAM_PHONE)
    assert "612345612" not in analysis.sender_hash
    assert analysis.latency_ms is not None


def test_message_body_is_not_persisted_in_analyses(
    api_client, db_session, consented_senior
):
    marker = "mensaje-prueba-sin-identificadores"
    message = f"{PHISHING} {marker}"
    body = sms_request(consented_senior.device.id, message, [PHISHING_URL])
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)

    assert response.status_code == 200
    analysis = db_session.get(Analysis, response.json()["analysis_id"])
    assert analysis is not None
    persisted_values = " ".join(
        str(getattr(analysis, column.name)) for column in Analysis.__table__.columns
    )
    assert marker not in persisted_values

    temp = db_session.get(TempContent, response.json()["analysis_id"])
    assert temp is not None
    assert temp.anonymized_text == message


def test_red_text_is_kept_30_days(db_session, red_response):
    temp = db_session.get(TempContent, red_response.json()["analysis_id"])
    assert temp.anonymized_text == PHISHING
    remaining = temp.delete_at - datetime.now(UTC)
    assert timedelta(days=29) < remaining <= timedelta(days=30)


# ES: Con CLASSIFIER_PROVIDER=ml este mensaje se clasifica como estafa (rojo),
#     no como spam (ámbar). El CI usa las reglas, así que el test siempre pasa en CI.
# EN: With CLASSIFIER_PROVIDER=ml this message is classified as scam (red),
#     not spam (amber). CI uses rules, so the test always passes in CI.
def test_amber_text_is_kept_7_days(api_client, db_session, consented_senior):
    body = sms_request(consented_senior.device.id, SPAM)
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)

    assert response.status_code == 200
    assert response.json()["risk_level"] == "amber"
    temp = db_session.get(TempContent, response.json()["analysis_id"])
    assert temp.anonymized_text == SPAM
    remaining = temp.delete_at - datetime.now(UTC)
    assert timedelta(days=6) < remaining <= timedelta(days=7)


def test_indicators_store_masked_phone_and_domain(db_session, red_response):
    public_values = set(db_session.scalars(select(Indicator.public_value)).all())
    assert {"+34 6** *** 12", "bbva-seguro.top"} <= public_values
    assert not any("612345612" in value for value in public_values)


# ---------- Alertas / Alerts ----------


def test_red_creates_alert_for_guardian(db_session, guardian, red_response):
    alert = db_session.scalar(
        select(Alert).where(Alert.analysis_id == red_response.json()["analysis_id"])
    )
    assert alert.guardian_id == guardian.id
    assert alert.summary == (
        "Hemos bloqueado un intento de estafa por SMS en el móvil de Carmen."
    )
    assert "[IBAN]" not in alert.explanation  # ES/EN: no message content
    assert {"type": "domain", "value": "bbva-seguro.top"}.items() <= (
        alert.evidence[0].items()
    )


# ---------- Reglas del contrato / Contract rules ----------


def test_automatic_without_consent_is_403(api_client, paired_senior):
    body = sms_request(paired_senior.device.id, PHISHING)
    response = api_client.post(ANALYSES, json=body, headers=paired_senior.headers)
    assert response.status_code == 403
    assert response.json()["code"] == "CONSENT_MISSING"


def test_not_anonymized_is_422(api_client, consented_senior):
    body = sms_request(consented_senior.device.id, PHISHING, applied=False)
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 422
    assert response.json()["code"] == "CONTENT_NOT_ANONYMIZED"


def test_other_device_id_is_403(api_client, consented_senior, guardian):
    body = sms_request(guardian.id, PHISHING)
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 403


def test_guardian_cannot_send_analyses(api_client, consented_senior, guardian_headers):
    body = sms_request(consented_senior.device.id, PHISHING)
    response = api_client.post(ANALYSES, json=body, headers=guardian_headers)
    assert response.status_code == 403


# ---------- Consulta de número / Phone lookup ----------


def test_unknown_number_asks_to_call_family(api_client, paired_senior):
    """ES: Consulta manual: no necesita consentimiento de monitorización.
    EN: Manual lookup: does not need monitoring consent.
    """
    response = api_client.post(
        ANALYSES,
        json=phone_lookup(paired_senior.device.id),
        headers=paired_senior.headers,
    )
    assert response.status_code == 200
    assert response.json()["block_template"] == "UNSURE_CALL_FAMILY"


def test_reported_number_is_red(api_client, db_session, paired_senior):
    now = datetime.now(UTC)
    db_session.add(
        Indicator(
            type=IndicatorType.PHONE,
            value_hash=hash_indicator(IndicatorType.PHONE, SPAM_PHONE),
            public_value="+34 6** *** 12",
            report_count=5,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    db_session.flush()
    response = api_client.post(
        ANALYSES,
        json=phone_lookup(paired_senior.device.id),
        headers=paired_senior.headers,
    )
    body = response.json()
    assert body["risk_level"] == "red"
    assert body["block_template"] == "SUSPICIOUS_CALL"


def test_invalid_phone_is_422(api_client, paired_senior):
    response = api_client.post(
        ANALYSES,
        json=phone_lookup(paired_senior.device.id, "+34 6"),
        headers=paired_senior.headers,
    )
    assert response.status_code == 422


# ---------- Rendimiento / Performance ----------


def test_fast_path_is_under_800_ms(db_session, red_response):
    analysis = db_session.get(Analysis, red_response.json()["analysis_id"])
    assert analysis.latency_ms < 800


# ---------- Enlaces dentro del texto / Links inside the text (#151) ----------

LINK_IN_TEXT = "Hola, aquí tienes la información: https://bbva-seguro.top/login"


def test_link_inside_text_is_checked(api_client, db_session, consented_senior):
    """ES: Sin `urls`, el enlace del texto también pasa por las reglas de enlaces.
    EN: Without `urls`, the link in the text also goes through the link rules.
    """
    body = sms_request(consented_senior.device.id, LINK_IN_TEXT)
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 200
    assert response.json()["risk_level"] == "red"
    assert response.json()["block_template"] == "DANGEROUS_LINK"

    temp = db_session.get(TempContent, response.json()["analysis_id"])
    assert temp.urls == ["https://bbva-seguro.top/login"]
    domain_hash = hash_indicator(IndicatorType.DOMAIN, "bbva-seguro.top")
    assert db_session.scalar(
        select(Indicator).where(Indicator.value_hash == domain_hash)
    )


def test_pasted_email_with_link_is_checked(api_client, consented_senior):
    body = sms_request(consented_senior.device.id, LINK_IN_TEXT)
    body.update(channel="manual", origin="manual")
    body.pop("sender")
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.status_code == 200
    assert response.json()["risk_level"] == "red"


def test_official_link_in_text_stays_green(api_client, consented_senior):
    body = sms_request(
        consented_senior.device.id, "Tu pedido llega mañana: https://amazon.es/pedido"
    )
    body["sender"] = {"type": "phone", "value": "+34699000111"}
    response = api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    assert response.json()["risk_level"] == "green"
