"""Comprueba que los enums coinciden con el Contrato Schemas v1.0.0.
Checks that the enums match the Schemas Contract v1.0.0.

ES: Si este test falla, alguien ha cambiado un enum sin actualizar el contrato.
EN: If this test fails, someone changed an enum without updating the contract.
"""

import pytest

from app.schemas import enums

CONTRACT = {
    enums.UserRole: ["senior", "guardian", "admin"],
    enums.Channel: ["sms", "notification", "screen", "call", "manual"],
    enums.InputType: [
        "text",
        "image",
        "audio",
        "video",
        "document",
        "url",
        "phone_number",
    ],
    enums.Origin: ["automatic", "manual"],
    enums.RiskLevel: ["green", "amber", "red"],
    enums.ThreatType: [
        "phishing",
        "smishing",
        "vishing",
        "spam",
        "identity_theft",
        "bank_fraud",
        "other",
        "none",
    ],
    enums.VerdictPhase: ["fast", "agent"],
    enums.Action: ["allow", "silent_block", "block_and_alert"],
    enums.BlockTemplate: [
        "FAKE_DO_NOT_TOUCH",
        "DANGEROUS_LINK",
        "SUSPICIOUS_CALL",
        "ASKS_BANK_DETAILS",
        "LOOKS_SAFE",
        "UNSURE_CALL_FAMILY",
    ],
    enums.AlertStatus: ["new", "seen", "confirmed_fraud", "false_positive"],
    enums.UnlockStatus: ["pending_guardian", "approved", "rejected", "expired"],
    enums.ConsentType: ["self", "legal_guardianship"],
    enums.IndicatorType: ["domain", "url", "phone", "alphanumeric_sender"],
    enums.RagSource: ["incibe", "osi", "policia_nacional", "banco_espana"],
    enums.CaseStatus: ["open", "in_review", "closed"],
}


@pytest.mark.parametrize("enum_cls, expected", CONTRACT.items())
def test_enum_values_match_contract(enum_cls, expected):
    """ES: Valores y orden idénticos al contrato. EN: Same values and order."""
    assert [member.value for member in enum_cls] == expected


def test_enum_serializes_as_plain_string():
    """ES: StrEnum se compara como texto. EN: StrEnum compares as plain text."""
    assert enums.RiskLevel.RED == "red"
