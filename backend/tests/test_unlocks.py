"""Tests de desbloqueos de falsos positivos (necesitan PostgreSQL).
False-positive unlock tests (need PostgreSQL).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import create_access_token, hash_password
from app.models.alert import Unlock as UnlockModel
from app.models.user import User
from app.schemas.enums import UserRole
from app.schemas.unlock import Unlock

UNLOCKS = "/api/v1/unlocks"
ANALYSES = "/api/v1/analyses"


def analyze(api_client, senior, text, urls=()):
    body = {
        "device_id": str(senior.device.id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-04T13:12:05Z",
        "content": {
            "text": text,
            "urls": list(urls),
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
    }
    return api_client.post(ANALYSES, json=body, headers=senior.headers).json()


@pytest.fixture
def blocked_analysis_id(api_client, consented_senior):
    verdict = analyze(
        api_client,
        consented_senior,
        "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique.",
        ["https://bbva-seguro.top/login"],
    )
    assert verdict["action"] == "block_and_alert"
    return verdict["analysis_id"]


@pytest.fixture
def pending(api_client, consented_senior, blocked_analysis_id):
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": blocked_analysis_id},
        headers=consented_senior.headers,
    )
    assert response.status_code == 201
    return response.json()


def stranger_headers(db_session, email="otro.tutor@example.com"):
    stranger = User(
        role=UserRole.GUARDIAN,
        display_name="Otro",
        email=email,
        password_hash=hash_password("contraseña-larga-2"),
    )
    db_session.add(stranger)
    db_session.flush()
    token = create_access_token(stranger.id, UserRole.GUARDIAN)
    return {"Authorization": f"Bearer {token}"}


# ---------- POST /unlocks ----------


def test_senior_requests_unlock(pending):
    unlock = Unlock.model_validate(pending)
    assert unlock.status == "pending_guardian"
    assert unlock.resolved_by is None
    ttl = unlock.expires_at - unlock.requested_at
    assert timedelta(hours=23) < ttl <= timedelta(hours=24)


def test_request_is_idempotent(api_client, consented_senior, pending):
    again = api_client.post(
        UNLOCKS,
        json={"analysis_id": pending["analysis_id"]},
        headers=consented_senior.headers,
    )
    assert again.json()["id"] == pending["id"]


def test_cannot_unlock_allowed_content(api_client, consented_senior):
    verdict = analyze(api_client, consented_senior, "Hola mamá, llego a las 8.")
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": verdict["analysis_id"]},
        headers=consented_senior.headers,
    )
    assert response.status_code == 422


def test_unknown_analysis_is_404(api_client, consented_senior):
    response = api_client.post(
        UNLOCKS,
        json={"analysis_id": str(uuid.uuid4())},
        headers=consented_senior.headers,
    )
    assert response.status_code == 404


def test_guardian_cannot_request_unlock(
    api_client, guardian_headers, blocked_analysis_id
):
    response = api_client.post(
        UNLOCKS, json={"analysis_id": blocked_analysis_id}, headers=guardian_headers
    )
    assert response.status_code == 403


# ---------- GET /unlocks ----------


def test_guardian_lists_pending(api_client, guardian_headers, pending):
    items = api_client.get(UNLOCKS, headers=guardian_headers).json()
    assert [item["id"] for item in items] == [pending["id"]]


def test_other_guardian_lists_nothing(api_client, db_session, pending):
    items = api_client.get(UNLOCKS, headers=stranger_headers(db_session)).json()
    assert items == []


def test_senior_polls_status(api_client, consented_senior, pending):
    response = api_client.get(
        f"{UNLOCKS}/{pending['id']}", headers=consented_senior.headers
    )
    assert response.json()["status"] == "pending_guardian"


# ---------- PATCH /unlocks/{id} ----------


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_guardian_resolves(api_client, guardian, guardian_headers, pending, decision):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": decision},
        headers=guardian_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == decision
    assert body["resolved_by"] == str(guardian.id)
    assert body["resolved_at"] is not None


def test_cannot_resolve_twice(api_client, guardian_headers, pending):
    url = f"{UNLOCKS}/{pending['id']}"
    api_client.patch(url, json={"status": "approved"}, headers=guardian_headers)
    second = api_client.patch(
        url, json={"status": "rejected"}, headers=guardian_headers
    )
    assert second.status_code == 409


def test_expired_request_cannot_be_resolved(
    api_client, db_session, guardian_headers, pending
):
    unlock = db_session.get(UnlockModel, uuid.UUID(pending["id"]))
    unlock.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.flush()

    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=guardian_headers,
    )
    assert response.status_code == 409
    assert db_session.get(UnlockModel, unlock.id).status == "expired"


@pytest.mark.parametrize("status", ["pending_guardian", "expired"])
def test_guardian_cannot_set_system_statuses(
    api_client, guardian_headers, pending, status
):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}", json={"status": status}, headers=guardian_headers
    )
    assert response.status_code == 422


def test_unpaired_guardian_gets_404(api_client, db_session, pending):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=stranger_headers(db_session, "otro2.tutor@example.com"),
    )
    assert response.status_code == 404


def test_senior_cannot_approve_own_request(api_client, consented_senior, pending):
    response = api_client.patch(
        f"{UNLOCKS}/{pending['id']}",
        json={"status": "approved"},
        headers=consented_senior.headers,
    )
    assert response.status_code == 403


# ---------- Respuestas simultáneas / Simultaneous answers (#142, ADR 0004) ----------


@pytest.fixture
def committed_unlock():
    """ES: Desbloqueo pendiente GUARDADO (commit) con dos Tutores vinculados.
    Las dos respuestas usan conexiones distintas, así que no sirve la sesión de
    test (no se confirma). Se borra todo al terminar.
    EN: Pending unlock COMMITTED with two paired guardians. Both answers use
    different connections, so the test session (never committed) is not enough.
    Everything is deleted afterwards.
    """
    from sqlalchemy import delete
    from sqlalchemy.exc import OperationalError

    from app.db.session import SessionLocal
    from app.models.analysis import Analysis
    from app.models.user import Device, Pairing
    from app.schemas.enums import (
        Action,
        Channel,
        InputType,
        Origin,
        RiskLevel,
        ThreatType,
        UnlockStatus,
        VerdictPhase,
    )

    try:
        session = SessionLocal()
        session.connection()
    except OperationalError:
        pytest.skip("PostgreSQL no disponible / PostgreSQL not available")

    now = datetime.now(UTC)
    suffix = uuid.uuid4().hex[:8]
    guardians = [
        User(
            role=UserRole.GUARDIAN,
            display_name=name,
            email=f"{name.lower()}.{suffix}@example.com",
            password_hash=hash_password("contraseña-larga-1"),
            is_verified=True,
        )
        for name in ("Lucia", "Pablo")
    ]
    senior = User(role=UserRole.SENIOR, display_name="Carmen")
    session.add_all([*guardians, senior])
    session.flush()
    device = Device(user_id=senior.id, platform="android", app_version="0.4.0")
    session.add(device)
    session.add_all(
        Pairing(
            guardian_id=guardian.id,
            senior_id=senior.id,
            code=f"{index:06d}",
            senior_display_name="Carmen",
            expires_at=now + timedelta(minutes=10),
            redeemed_at=now,
        )
        for index, guardian in enumerate(guardians)
    )
    session.flush()
    analysis = Analysis(
        device_id=device.id,
        channel=Channel.SMS,
        origin=Origin.AUTOMATIC,
        input_types=[InputType.TEXT],
        received_at=now,
        risk_level=RiskLevel.RED,
        threat_type=ThreatType.SMISHING,
        action=Action.BLOCK_AND_ALERT,
        block_template="DANGEROUS_LINK",
        phase=VerdictPhase.FAST,
        model_version="test",
    )
    session.add(analysis)
    session.flush()
    unlock = UnlockModel(
        analysis_id=analysis.id,
        status=UnlockStatus.PENDING_GUARDIAN,
        expires_at=now + timedelta(minutes=30),
    )
    session.add(unlock)
    session.commit()
    ids = {
        "unlock": unlock.id,
        "analysis": analysis.id,
        "device": device.id,
        "users": [g.id for g in guardians] + [senior.id],
        "guardians": [g.id for g in guardians],
    }
    session.close()
    yield ids

    with SessionLocal() as cleanup:
        cleanup.execute(delete(UnlockModel).where(UnlockModel.id == ids["unlock"]))
        cleanup.execute(delete(Analysis).where(Analysis.id == ids["analysis"]))
        cleanup.execute(delete(Pairing).where(Pairing.senior_id == ids["users"][-1]))
        cleanup.execute(delete(Device).where(Device.id == ids["device"]))
        cleanup.execute(delete(User).where(User.id.in_(ids["users"])))
        cleanup.commit()


def _waiting_on_lock(session) -> int:
    from sqlalchemy import text

    count = session.scalar(
        text(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE wait_event_type = 'Lock' AND datname = current_database()"
        )
    )
    # ES: pg_stat_activity se congela dentro de una transacción: cerrarla para
    #     ver el estado actual en la siguiente consulta.
    # EN: pg_stat_activity is frozen within a transaction: end it to see the
    #     current state on the next query.
    session.rollback()
    return count


def test_simultaneous_answers_first_wins(committed_unlock):
    """ES: Dos Tutores responden a la vez. Se fuerza el choque: una tercera
    conexión bloquea la fila, las dos peticiones esperan en el FOR UPDATE y
    después se libera. Una recibe 200, la otra 409 y queda guardada la primera.
    EN: Two guardians answer at once. The clash is forced: a third connection
    locks the row, both requests wait on FOR UPDATE, then it is released. One
    gets 200, the other 409, and the first answer is the one stored.
    """
    import threading
    import time

    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.main import app

    url = f"{UNLOCKS}/{committed_unlock['unlock']}"
    answers = dict(zip(committed_unlock["guardians"], ("approved", "rejected")))
    results: dict[uuid.UUID, int] = {}

    def answer(guardian_id: uuid.UUID) -> None:
        token = create_access_token(guardian_id, UserRole.GUARDIAN)
        response = TestClient(app).patch(
            url,
            json={"status": answers[guardian_id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        results[guardian_id] = response.status_code

    holder = SessionLocal()
    observer = SessionLocal()
    try:
        holder.scalar(
            select(UnlockModel)
            .where(UnlockModel.id == committed_unlock["unlock"])
            .with_for_update()
        )
        threads = [
            threading.Thread(target=answer, args=(g,))
            for g in committed_unlock["guardians"]
        ]
        for thread in threads:
            thread.start()

        # ES/EN: wait until both requests are blocked on the row lock
        deadline = time.monotonic() + 10
        while _waiting_on_lock(observer) < 2:
            assert time.monotonic() < deadline, "requests never reached the lock"
            time.sleep(0.05)
        holder.rollback()  # ES/EN: release the lock: both race for it now

        for thread in threads:
            thread.join(timeout=10)
            assert not thread.is_alive()
    finally:
        holder.close()
        observer.close()

    assert sorted(results.values()) == [200, 409]
    winner = next(g for g, code in results.items() if code == 200)
    with SessionLocal() as check:
        stored = check.get(UnlockModel, committed_unlock["unlock"])
        assert stored.status == answers[winner]
        assert stored.resolved_by == winner
