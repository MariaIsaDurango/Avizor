"""Tests de HMAC y enmascarado de teléfonos.
HMAC and phone masking tests.
"""

import hashlib
import hmac

import pytest

from app.core.config import settings
from app.core.privacy import (
    InvalidPhoneError,
    hash_indicator,
    mask_phone,
    normalize_phone,
    public_value,
)
from app.schemas.enums import IndicatorType

PHONE = IndicatorType.PHONE

# ES: Números inventados. EN: Fake numbers.
CARMEN_SPAM = "+34612345612"


@pytest.mark.parametrize(
    "value", ["+34612345612", "612 345 612", "612-345-612", "+34 612 34 56 12"]
)
def test_normalize_phone_to_e164(value):
    assert normalize_phone(value) == "+34612345612"


@pytest.mark.parametrize("value", ["abc", "123", "+34 6"])
def test_invalid_phone(value):
    with pytest.raises(InvalidPhoneError):
        normalize_phone(value)


def test_mask_matches_contract_example():
    assert mask_phone(CARMEN_SPAM) == "+34 6** *** 12"


def test_mask_does_not_reveal_length():
    short, long_ = mask_phone("+34912345645"), mask_phone("+16502530000")
    assert len(short.split(" ", 1)[1]) == len(long_.split(" ", 1)[1])


def test_mask_never_contains_full_number():
    assert "612345612" not in mask_phone(CARMEN_SPAM)


def test_hash_is_hmac_sha256_with_server_key():
    expected = hmac.new(
        settings.PHONE_HMAC_KEY.encode(), b"phone:+34612345612", hashlib.sha256
    ).hexdigest()
    assert hash_indicator(PHONE, CARMEN_SPAM) == expected


def test_same_number_in_any_format_gives_same_hash():
    """ES: Para contar reportes del mismo atacante. EN: To count reports per attacker."""
    assert hash_indicator(PHONE, "612 345 612") == hash_indicator(PHONE, CARMEN_SPAM)


def test_hash_does_not_contain_the_number():
    assert "612345612" not in hash_indicator(PHONE, CARMEN_SPAM)


def test_hash_depends_on_type():
    """ES: Un dominio y un remitente iguales no chocan. EN: No cross-type collisions."""
    assert hash_indicator(IndicatorType.DOMAIN, "bbva") != hash_indicator(
        IndicatorType.ALPHANUMERIC_SENDER, "bbva"
    )


def test_domain_is_case_insensitive_and_public():
    domain = IndicatorType.DOMAIN
    assert hash_indicator(domain, "BBVA-seguro.top") == hash_indicator(
        domain, "bbva-seguro.top"
    )
    assert public_value(domain, " BBVA-seguro.TOP ") == "bbva-seguro.top"


def test_phone_public_value_is_masked():
    assert public_value(PHONE, "612 345 612") == "+34 6** *** 12"


def test_alphanumeric_sender_is_uppercased():
    sender = IndicatorType.ALPHANUMERIC_SENDER
    assert public_value(sender, " bbva ") == "BBVA"
