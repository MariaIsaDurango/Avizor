"""Protección de teléfonos y remitentes: HMAC + versión enmascarada.
Phone and sender protection: HMAC + masked version.

ES: El número en claro nunca se guarda. Se guarda:
    - value_hash: HMAC-SHA256 con la clave del servidor (para contar reportes).
    - public_value: versión enmascarada (+34 6** *** 12) para el portal.
    La app nunca conoce la clave del HMAC.
EN: The plain number is never stored. We store:
    - value_hash: HMAC-SHA256 with the server key (to count reports).
    - public_value: masked version (+34 6** *** 12) for the portal.
    The app never knows the HMAC key.
"""

import hashlib
import hmac

import phonenumbers

from app.core.config import settings
from app.schemas.enums import IndicatorType

DEFAULT_REGION = "ES"


class InvalidPhoneError(ValueError):
    """ES: El número no es un teléfono posible. EN: Not a possible phone number."""


def normalize_phone(value: str, default_region: str = DEFAULT_REGION) -> str:
    """ES: Devuelve el número en E.164 (+34612345612). Acepta "612 345 612".
    EN: Returns the number in E.164 (+34612345612). Accepts "612 345 612".
    """
    try:
        number = phonenumbers.parse(value, default_region)
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneError(value) from exc
    # ES: is_possible (no is_valid): los estafadores usan rangos raros.
    # EN: is_possible (not is_valid): scammers use unusual ranges.
    if not phonenumbers.is_possible_number(number):
        raise InvalidPhoneError(value)
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def mask_phone(e164: str) -> str:
    """ES: "+34612345612" → "+34 6** *** 12". Misma forma para cualquier longitud,
    así no se revela cuántas cifras tiene.
    EN: "+34612345612" → "+34 6** *** 12". Same shape for any length,
    so the number of digits is not revealed.
    """
    number = phonenumbers.parse(e164, None)
    national = str(number.national_number)
    return f"+{number.country_code} {national[0]}** *** {national[-2:]}"


def _normalize(indicator_type: IndicatorType, value: str) -> str:
    if indicator_type == IndicatorType.PHONE:
        return normalize_phone(value)
    if indicator_type == IndicatorType.ALPHANUMERIC_SENDER:
        return value.strip().upper()
    # ES: Dominios y URLs sin distinguir mayúsculas. EN: Case-insensitive.
    return value.strip().lower()


def hash_indicator(indicator_type: IndicatorType, value: str) -> str:
    """ES: HMAC-SHA256 del valor normalizado (mismo número → mismo hash).
    EN: HMAC-SHA256 of the normalized value (same number → same hash).
    """
    message = f"{indicator_type.value}:{_normalize(indicator_type, value)}"
    return hmac.new(
        settings.PHONE_HMAC_KEY.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def public_value(indicator_type: IndicatorType, value: str) -> str:
    """ES: Lo que se puede mostrar: teléfonos enmascarados, resto normalizado.
    EN: What can be shown: masked phones, everything else normalized.
    """
    normalized = _normalize(indicator_type, value)
    if indicator_type == IndicatorType.PHONE:
        return mask_phone(normalized)
    return normalized
