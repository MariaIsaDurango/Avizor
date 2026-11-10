"""Enums compartidos del Contrato Schemas v1.0.0.
Shared enums from the Schemas Contract v1.0.0.

ES: Deben coincidir EXACTAMENTE con los ENUM de PostgreSQL y los tipos de la app.
    Añadir un valor = versión MINOR. Eliminar o renombrar = versión MAJOR.
EN: Must match EXACTLY the PostgreSQL ENUMs and the app types.
    Adding a value = MINOR version. Removing or renaming = MAJOR version.
"""

from enum import StrEnum


class UserRole(StrEnum):
    SENIOR = "senior"
    GUARDIAN = "guardian"  # ES: Tutor / EN: guardian (family member)
    ADMIN = "admin"


class Channel(StrEnum):
    SMS = "sms"
    NOTIFICATION = "notification"
    SCREEN = "screen"
    CALL = "call"
    MANUAL = "manual"


class InputType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    URL = "url"
    PHONE_NUMBER = "phone_number"


class Origin(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class RiskLevel(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class ThreatType(StrEnum):
    PHISHING = "phishing"
    SMISHING = "smishing"
    VISHING = "vishing"
    SPAM = "spam"
    IDENTITY_THEFT = "identity_theft"
    BANK_FRAUD = "bank_fraud"
    OTHER = "other"
    NONE = "none"


class VerdictPhase(StrEnum):
    FAST = "fast"
    AGENT = "agent"


class Action(StrEnum):
    ALLOW = "allow"
    SILENT_BLOCK = "silent_block"
    BLOCK_AND_ALERT = "block_and_alert"


class BlockTemplate(StrEnum):
    FAKE_DO_NOT_TOUCH = "FAKE_DO_NOT_TOUCH"
    DANGEROUS_LINK = "DANGEROUS_LINK"
    SUSPICIOUS_CALL = "SUSPICIOUS_CALL"
    ASKS_BANK_DETAILS = "ASKS_BANK_DETAILS"
    LOOKS_SAFE = "LOOKS_SAFE"
    UNSURE_CALL_FAMILY = "UNSURE_CALL_FAMILY"


class AlertStatus(StrEnum):
    NEW = "new"
    SEEN = "seen"
    CONFIRMED_FRAUD = "confirmed_fraud"
    FALSE_POSITIVE = "false_positive"


class UnlockStatus(StrEnum):
    PENDING_GUARDIAN = "pending_guardian"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ConsentType(StrEnum):
    SELF = "self"
    LEGAL_GUARDIANSHIP = "legal_guardianship"


class IndicatorType(StrEnum):
    DOMAIN = "domain"
    URL = "url"
    PHONE = "phone"
    ALPHANUMERIC_SENDER = "alphanumeric_sender"


class RagSource(StrEnum):
    INCIBE = "incibe"
    OSI = "osi"
    POLICIA_NACIONAL = "policia_nacional"
    BANCO_ESPANA = "banco_espana"


class CaseStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


class RedactedEntity(StrEnum):
    """Etiquetas de censura del NER / NER redaction tags.

    ES: En el texto anonimizado aparecen como [NAME], [IBAN]...
    EN: They appear in the anonymized text as [NAME], [IBAN]...
    """

    NAME = "NAME"
    ID_NUMBER = "ID_NUMBER"  # ES: DNI / NIE  EN: Spanish ID documents
    IBAN = "IBAN"
    CARD = "CARD"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    ADDRESS = "ADDRESS"


class ErrorCode(StrEnum):
    """Códigos de error reservados / Reserved error codes (RFC 9457)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONSENT_MISSING = "CONSENT_MISSING"
    PAIRING_EXPIRED = "PAIRING_EXPIRED"
    CONTENT_NOT_ANONYMIZED = "CONTENT_NOT_ANONYMIZED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
