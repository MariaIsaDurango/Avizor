"""Integration test for the tutor-to-senior MVP flow."""

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
PAIRINGS = "/api/v1/pairings"
REDEEM = "/api/v1/pairings/redeem"
CONSENTS = "/api/v1/consents"
ANALYSES = "/api/v1/analyses"
ALERTS = "/api/v1/alerts"
UNLOCKS = "/api/v1/unlocks"


def test_registration_pairing_analysis_alert_and_unlock(api_client):
    guardian = {
        "email": "flujo.qa@example.com",
        "password": "contraseña-larga-1",
        "display_name": "Tutor de prueba",
    }
    registered = api_client.post(REGISTER, json=guardian)
    assert registered.status_code == 201

    login = api_client.post(
        LOGIN,
        json={"email": guardian["email"], "password": guardian["password"]},
    )
    assert login.status_code == 200
    guardian_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    pairing = api_client.post(
        PAIRINGS,
        json={"senior_display_name": "Carmen de prueba"},
        headers=guardian_headers,
    )
    assert pairing.status_code == 201

    redeemed = api_client.post(
        REDEEM,
        json={
            "code": pairing.json()["code"],
            "device": {
                "platform": "android",
                "app_version": "0.4.0",
                "push_token": None,
            },
        },
    )
    assert redeemed.status_code == 200
    senior = redeemed.json()
    senior_headers = {"Authorization": f"Bearer {senior['access_token']}"}

    consent = api_client.post(
        CONSENTS,
        json={
            "senior_id": senior["senior_id"],
            "type": "self",
            "scope": ["sms"],
            "text_version": "qa-flow-test",
            "granted_by": senior["senior_id"],
            "evidence": None,
            "granted_at": "2026-11-17T10:00:00Z",
        },
        headers=senior_headers,
    )
    assert consent.status_code == 201

    analysis = api_client.post(
        ANALYSES,
        json={
            "device_id": senior["device_id"],
            "channel": "sms",
            "origin": "automatic",
            "input_type": "text",
            "received_at": "2026-11-17T10:00:00Z",
            "sender": {"type": "phone", "value": "+34612345612"},
            "content": {
                "text": "Aviso de prueba: cuenta [IBAN] bloqueada.",
                "urls": ["https://bbva-seguro.top/login"],
                "language": "es",
                "anonymization": {
                    "applied": True,
                    "ner_model_version": "qa-test",
                    "redacted_entities": ["IBAN"],
                },
            },
            "app": {"version": "0.4.0", "android_api": 34},
        },
        headers=senior_headers,
    )
    assert analysis.status_code == 200
    analysis_body = analysis.json()
    assert analysis_body["risk_level"] == "red"

    alerts = api_client.get(ALERTS, headers=guardian_headers)
    assert alerts.status_code == 200
    assert len(alerts.json()["items"]) == 1
    assert alerts.json()["items"][0]["status"] == "new"

    unlock = api_client.post(
        UNLOCKS,
        json={"analysis_id": analysis_body["analysis_id"]},
        headers=senior_headers,
    )
    assert unlock.status_code == 201

    resolved = api_client.patch(
        f"{UNLOCKS}/{unlock.json()['id']}",
        json={"status": "approved"},
        headers=guardian_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "approved"

    final_status = api_client.get(
        f"{UNLOCKS}/{unlock.json()['id']}", headers=senior_headers
    )
    assert final_status.status_code == 200
    assert final_status.json()["status"] == "approved"
