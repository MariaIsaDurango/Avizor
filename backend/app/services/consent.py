"""Registro de consentimientos de monitorización (RGPD).
Monitoring consent records (GDPR).

ES: Reglas:
  - type=self: solo el propio Sénior, desde su dispositivo.
  - type=legal_guardianship: solo un Tutor vinculado, con evidencia.
  - granted_by y granted_at los pone el servidor (no se confía en el cliente).
EN: Rules:
  - type=self: only the senior, from their own device.
  - type=legal_guardianship: only a paired guardian, with evidence.
  - granted_by and granted_at are set by the server (client is not trusted).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import any_, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenPayload
from app.models.user import Consent
from app.schemas.consent import Consent as ConsentSchema
from app.schemas.consent import ConsentRead
from app.schemas.enums import Channel, ConsentType, ErrorCode, UserRole
from app.services.identity import is_paired, senior_id_from_device


def _forbidden(detail: str) -> ApiError:
    return ApiError(403, ErrorCode.FORBIDDEN, detail)


def _granted_by(db: Session, token: TokenPayload, body: ConsentSchema) -> uuid.UUID:
    """ES: Comprueba quién puede consentir y devuelve el id de quien consiente.
    EN: Checks who may consent and returns the id of who consents.
    """
    if body.type == ConsentType.SELF:
        if token.role != UserRole.SENIOR:
            raise _forbidden("Solo el usuario sénior puede dar su consentimiento.")
        senior_id = senior_id_from_device(db, token.sub)
        if senior_id != body.senior_id:
            raise _forbidden("Solo puedes consentir por ti mismo.")
        return senior_id

    # ES: Tutela legal. EN: Legal guardianship.
    if token.role != UserRole.GUARDIAN:
        raise _forbidden("La tutela legal la acredita el tutor.")
    if not is_paired(db, token.sub, body.senior_id):
        raise _forbidden("No estás vinculado a este usuario sénior.")
    return token.sub


def create_consent(
    db: Session, token: TokenPayload, body: ConsentSchema
) -> ConsentRead:
    granted_by = _granted_by(db, token, body)
    if body.granted_by != granted_by:
        raise _forbidden("granted_by no coincide con quien da el consentimiento.")

    consent = Consent(
        senior_id=body.senior_id,
        type=body.type,
        scope=list(body.scope),
        text_version=body.text_version,
        granted_by=granted_by,
        evidence=body.evidence.model_dump() if body.evidence else None,
        # ES: Hora del servidor: prueba fiable para el RGPD.
        # EN: Server time: reliable evidence for GDPR.
        granted_at=datetime.now(UTC),
    )
    db.add(consent)
    db.commit()
    return ConsentRead.model_validate(consent, from_attributes=True)


def has_active_consent(db: Session, senior_id: uuid.UUID, channel: Channel) -> bool:
    """ES: ¿Hay un consentimiento vigente que cubra este canal? (lo usará #14)
    EN: Is there an active consent covering this channel? (used by #14)
    """
    return (
        db.scalar(
            select(Consent.id).where(
                Consent.senior_id == senior_id,
                Consent.revoked_at.is_(None),
                channel == any_(Consent.scope),
            )
        )
        is not None
    )


def revoke_consent(
    db: Session, token: TokenPayload, consent_id: uuid.UUID
) -> ConsentRead:
    """ES: RGPD: el consentimiento se puede retirar en cualquier momento.
    Lo retira quien pudo darlo: el Sénior (self) o un Tutor vinculado (tutela).
    EN: GDPR: consent can be withdrawn at any time.
    Whoever could grant it can revoke it: the senior (self) or a paired guardian.
    """
    consent = db.get(Consent, consent_id)
    # ES: 404 también si no tiene permiso: no revela que existe.
    # EN: 404 also when not allowed: does not reveal that it exists.
    not_found = ApiError(404, ErrorCode.NOT_FOUND, "Consentimiento no encontrado.")
    if consent is None:
        raise not_found

    if consent.type == ConsentType.SELF:
        allowed = (
            token.role == UserRole.SENIOR
            and senior_id_from_device(db, token.sub) == consent.senior_id
        )
    else:
        allowed = token.role == UserRole.GUARDIAN and is_paired(
            db, token.sub, consent.senior_id
        )
    if not allowed:
        raise not_found

    # ES: Revocar dos veces no cambia la fecha. EN: Revoking twice keeps the date.
    if consent.revoked_at is None:
        consent.revoked_at = datetime.now(UTC)
        db.commit()
    return ConsentRead.model_validate(consent, from_attributes=True)
