"""Endpoints de dispositivos del Tutor (añadido MINOR al contrato).
Guardian device endpoints (MINOR addition to the contract).
"""

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession, GuardianToken
from app.schemas.device import DeviceRead, GuardianDeviceRegister
from app.services import devices as device_service

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("", status_code=status.HTTP_201_CREATED)
def register_device(
    body: GuardianDeviceRegister, db: DbSession, token: GuardianToken
) -> DeviceRead:
    """ES: La app Tutor lo llama al iniciar sesión o si cambia el token push.
    EN: The guardian app calls it on login or when the push token changes.
    """
    device = device_service.register_guardian_device(db, token.sub, body)
    return DeviceRead.model_validate(device, from_attributes=True)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(device_id: uuid.UUID, db: DbSession, token: GuardianToken):
    device_service.delete_guardian_device(db, token.sub, device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
