"""Tests de Alert, PushNotification, Unlock y ProblemDetail.
Tests for Alert, PushNotification, Unlock and ProblemDetail.
"""

import pytest
from pydantic import ValidationError

from app.schemas.alert import (
    Alert,
    AlertUpdate,
    IndicatorEvidence,
    OfficialNoticeEvidence,
    PushNotification,
)
from app.schemas.problem import ProblemDetail
from app.schemas.unlock import Unlock, UnlockUpdate

# ES: Ejemplos copiados del contrato. EN: Examples copied from the contract.
ALERT = {
    "id": "e2d4f6a8-1b3c-4d5e-8f9a-0b1c2d3e4f5a",
    "analysis_id": "a4b8c2d1-6e3f-4c9a-8b7d-1e2f3a4b5c6d",
    "senior_id": "9c8b7a6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d",
    "senior_name": "Carmen",
    "risk_level": "red",
    "threat_type": "smishing",
    "channel": "sms",
    "summary": "Hemos bloqueado un intento de estafa por SMS en el móvil de Carmen.",
    "explanation": "El mensaje imita al BBVA y enlaza a un dominio registrado hace 3 días.",
    "evidence": [
        {
            "type": "domain",
            "value": "bbva-seguro.top",
            "reason": "Dominio reciente con marca bancaria",
        },
        {
            "type": "official_notice",
            "source": "incibe",
            "url": "https://www.incibe.es/aviso",
        },
    ],
    "status": "new",
    "created_at": "2026-11-04T13:12:06Z",
}

UNLOCK = {
    "id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
    "analysis_id": "a4b8c2d1-6e3f-4c9a-8b7d-1e2f3a4b5c6d",
    "status": "pending_guardian",
    "requested_at": "2026-11-04T13:20:00Z",
    "expires_at": "2026-11-05T13:20:00Z",
    "resolved_by": None,
    "resolved_at": None,
}

PROBLEM = {
    "type": "https://escudofamiliar.app/errors/consent-missing",
    "title": "Falta el consentimiento del usuario sénior",
    "status": 403,
    "code": "CONSENT_MISSING",
    "detail": "El dispositivo no tiene un consentimiento de monitorización vigente.",
    "trace_id": "8b1d4c2e-7f3a-4e19-9a0b-2c6d5e8f1a73",
}


# ---------- Alert ----------


def test_alert_contract_example_is_valid():
    alert = Alert.model_validate(ALERT)
    assert isinstance(alert.evidence[0], IndicatorEvidence)
    assert isinstance(alert.evidence[1], OfficialNoticeEvidence)


def test_alert_only_for_red():
    """ES: amber no genera alerta. EN: amber does not create alerts."""
    with pytest.raises(ValidationError):
        Alert.model_validate({**ALERT, "risk_level": "amber"})


def test_official_notice_with_unknown_source_fails():
    """ES: El LLM no puede inventar fuentes. EN: The LLM cannot invent sources."""
    evidence = [
        {"type": "official_notice", "source": "wikipedia", "url": "https://x.es"}
    ]
    with pytest.raises(ValidationError):
        Alert.model_validate({**ALERT, "evidence": evidence})


def test_guardian_cannot_set_alert_back_to_new():
    with pytest.raises(ValidationError):
        AlertUpdate.model_validate({"status": "new"})


def test_guardian_can_mark_false_positive():
    assert AlertUpdate.model_validate({"status": "false_positive"})


def test_push_body_is_short():
    """ES: El push no puede llevar el mensaje. EN: Push cannot carry the message."""
    with pytest.raises(ValidationError):
        PushNotification.model_validate(
            {"alert_id": ALERT["id"], "title": "Estafa bloqueada", "body": "a" * 121}
        )


# ---------- Unlock ----------


def test_unlock_contract_example_is_valid():
    assert Unlock.model_validate(UNLOCK).status == "pending_guardian"


@pytest.mark.parametrize("status", ["pending_guardian", "expired"])
def test_guardian_cannot_set_system_statuses(status):
    with pytest.raises(ValidationError):
        UnlockUpdate.model_validate({"status": status})


# ---------- ProblemDetail ----------


def test_problem_contract_example_is_valid():
    assert ProblemDetail.model_validate(PROBLEM).code == "CONSENT_MISSING"


def test_problem_rejects_unknown_code():
    with pytest.raises(ValidationError):
        ProblemDetail.model_validate({**PROBLEM, "code": "SOMETHING_ELSE"})
