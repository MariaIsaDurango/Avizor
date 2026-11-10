"""Tests de los schemas Pairing y Consent.
Tests for the Pairing and Consent schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.consent import Consent
from app.schemas.enums import ConsentType
from app.schemas.pairing import PairingRead, PairingRedeem

SENIOR_ID = "9c8b7a6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
GUARDIAN_ID = "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"

# ES: Ejemplo copiado del contrato. EN: Example copied from the contract.
CONSENT_SELF = {
    "senior_id": SENIOR_ID,
    "type": "self",
    "scope": ["sms", "notification", "screen", "call"],
    "text_version": "accessibility-notice-2026-11",
    "granted_by": SENIOR_ID,
    "evidence": None,
    "granted_at": "2026-11-04T10:00:00Z",
}


def test_consent_contract_example_is_valid():
    consent = Consent.model_validate(CONSENT_SELF)
    assert consent.type == ConsentType.SELF


def test_legal_guardianship_without_evidence_fails():
    data = {**CONSENT_SELF, "type": "legal_guardianship", "granted_by": GUARDIAN_ID}
    with pytest.raises(ValidationError):
        Consent.model_validate(data)


def test_legal_guardianship_with_evidence_is_valid():
    data = {
        **CONSENT_SELF,
        "type": "legal_guardianship",
        "granted_by": GUARDIAN_ID,
        "evidence": {"document": "court_ruling", "reference": "JDO-123/2026"},
    }
    assert Consent.model_validate(data).evidence is not None


def test_consent_rejects_unknown_channel():
    with pytest.raises(ValidationError):
        Consent.model_validate({**CONSENT_SELF, "scope": ["whatsapp"]})


def test_consent_rejects_date_without_timezone():
    """ES: Las fechas deben ir en UTC con zona. EN: Dates must include a timezone."""
    with pytest.raises(ValidationError):
        Consent.model_validate({**CONSENT_SELF, "granted_at": "2026-11-04T10:00:00"})


def test_consent_ignores_unknown_fields():
    """ES: Regla del contrato. EN: Contract rule."""
    assert Consent.model_validate({**CONSENT_SELF, "extra_field": 1})


@pytest.mark.parametrize("code", ["12345", "1234567", "abcdef", "12 345"])
def test_pairing_code_must_be_six_digits(code):
    with pytest.raises(ValidationError):
        PairingRedeem.model_validate(
            {"code": code, "device": {"platform": "android", "app_version": "0.4.0"}}
        )


def test_pairing_redeem_valid():
    redeem = PairingRedeem.model_validate(
        {"code": "482913", "device": {"platform": "android", "app_version": "0.4.0"}}
    )
    assert redeem.device.platform == "android"


def test_pairing_read_valid():
    pairing = PairingRead.model_validate(
        {
            "id": "3f2a9c1e-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
            "code": "482913",
            "expires_at": "2026-11-04T10:10:00Z",
        }
    )
    assert pairing.code == "482913"
