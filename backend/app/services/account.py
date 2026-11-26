"""Baja de cuenta: borrado físico de los datos del usuario (#194).
Account deletion: physical removal of the user's data (#194).

ES: Solo para quien tiene cuenta propia (Tutor y senior_solo). Se borran el
    usuario, sus dispositivos, sus análisis (con sus adjuntos, texto temporal,
    alertas y desbloqueos), sus consentimientos, sus alertas y sus vínculos.
    Los indicadores agregados (dominios, teléfonos con HMAC) se quedan: no
    identifican a la persona. Los casos del panel pierden el enlace al análisis.
    Al desaparecer el usuario, sus tokens dejan de valer (401).
EN: Only for users with their own account (guardian and senior_solo). The
    user, their devices, their analyses (with attachments, temp text, alerts
    and unlocks), their consents, their alerts and their pairings are deleted.
    Aggregated indicators (domains, HMAC phones) stay: they do not identify
    the person. Panel cases lose the link to the analysis.
    Once the user is gone their tokens stop working (401).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import TokenPayload, verify_password
from app.models.alert import Alert, Unlock
from app.models.analysis import Analysis
from app.models.indicator import Case, IndicatorReport
from app.models.user import Consent, Device, Pairing, User
from app.schemas.enums import ErrorCode, UserRole

ACCOUNT_ROLES = (UserRole.GUARDIAN, UserRole.SENIOR_SOLO)
WRONG_PASSWORD = "La contraseña no es correcta."


def retire_senior_if_unpaired(db: Session, senior_id: uuid.UUID) -> None:
    """ES: Si al Sénior vinculado no le queda ningún Tutor, se le da de baja
    (deleted_at) y se borra el push_token de sus móviles: su token deja de valer
    y no recibe más avisos. Sus análisis se borran con la retención normal.
    EN: If the paired senior has no guardian left, they are deactivated
    (deleted_at) and their phones' push_token is cleared: their token stops
    working and no more notifications are sent. Their analyses are removed by
    normal retention.
    """
    still_linked = db.scalar(
        select(Pairing.id).where(
            Pairing.senior_id == senior_id, Pairing.active.is_(True)
        )
    )
    if still_linked is not None:
        return
    senior = db.get(User, senior_id)
    if senior is not None and senior.deleted_at is None:
        senior.deleted_at = datetime.now(UTC)
    db.execute(
        update(Device).where(Device.user_id == senior_id).values(push_token=None)
    )


def _account_user(db: Session, token: TokenPayload) -> User:
    if token.role == UserRole.SENIOR_SOLO:
        device = db.get(Device, token.sub)
        user = db.get(User, device.user_id) if device else None
    else:
        user = db.get(User, token.sub)
    if user is None or user.deleted_at is not None:
        raise ApiError(401, ErrorCode.UNAUTHENTICATED, "Usuario no encontrado.")
    return user


def delete_account(db: Session, token: TokenPayload, password: str) -> None:
    """ES: Pide la contraseña otra vez: un móvil desbloqueado no basta para
    borrar la cuenta. EN: Asks for the password again: an unlocked phone is not
    enough to delete the account.
    """
    if token.role not in ACCOUNT_ROLES:
        raise ApiError(403, ErrorCode.FORBIDDEN, "Este perfil no tiene cuenta propia.")
    user = _account_user(db, token)
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise ApiError(400, ErrorCode.VALIDATION_ERROR, WRONG_PASSWORD)
    user_id = user.id

    # ES: Sénior que se quedan sin este Tutor. EN: Seniors losing this guardian.
    senior_ids = set(
        db.scalars(
            select(Pairing.senior_id).where(
                Pairing.guardian_id == user_id,
                Pairing.active.is_(True),
                Pairing.senior_id.is_not(None),
            )
        )
    )

    device_ids = select(Device.id).where(Device.user_id == user_id)
    analysis_ids = select(Analysis.id).where(Analysis.device_id.in_(device_ids))
    db.execute(delete(Alert).where(Alert.analysis_id.in_(analysis_ids)))
    db.execute(delete(Unlock).where(Unlock.analysis_id.in_(analysis_ids)))
    db.execute(
        update(Case).where(Case.analysis_id.in_(analysis_ids)).values(analysis_id=None)
    )
    # ES: Adjuntos y texto temporal caen en cascada. EN: Attachments and temp
    #     text go by cascade.
    db.execute(delete(Analysis).where(Analysis.device_id.in_(device_ids)))
    db.execute(delete(IndicatorReport).where(IndicatorReport.device_id.in_(device_ids)))
    db.execute(delete(Device).where(Device.user_id == user_id))

    db.execute(delete(Alert).where(Alert.guardian_id == user_id))
    db.execute(
        update(Unlock).where(Unlock.resolved_by == user_id).values(resolved_by=None)
    )
    db.execute(update(Case).where(Case.assigned_to == user_id).values(assigned_to=None))
    db.execute(
        delete(Consent).where(
            or_(Consent.senior_id == user_id, Consent.granted_by == user_id)
        )
    )
    db.execute(
        delete(Pairing).where(
            or_(Pairing.guardian_id == user_id, Pairing.senior_id == user_id)
        )
    )
    db.execute(delete(User).where(User.id == user_id))
    db.flush()

    for senior_id in senior_ids:
        retire_senior_if_unpaired(db, senior_id)
    db.commit()
