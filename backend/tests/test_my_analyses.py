"""Tests del historial del Sénior sin Tutor (#175). Necesitan PostgreSQL.
History tests for the senior without a guardian (#175). They need PostgreSQL.
"""

import uuid

import pytest
from conftest import ANALYSES, PHISHING, analysis_body

MY_ANALYSES = "/api/v1/my-analyses"
SAFE = "Hola mamá, llego a las 8 para cenar."


def analyze(api_client, headers, text):
    response = api_client.post(ANALYSES, json=analysis_body(text), headers=headers)
    assert response.status_code == 200
    return response.json()["analysis_id"]


def test_empty_history(api_client, solo):
    response = api_client.get(MY_ANALYSES, headers=solo["headers"])
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_history_lists_own_analyses_newest_first(
    api_client,
    consented_solo,
):
    headers = consented_solo["headers"]
    first = analyze(api_client, headers, SAFE)
    second = analyze(api_client, headers, PHISHING)

    data = api_client.get(MY_ANALYSES, headers=headers).json()
    assert data["total"] == 2
    by_id = {item["analysis_id"]: item for item in data["items"]}
    assert set(by_id) == {first, second}
    newest = by_id[second]
    assert newest["risk_level"] == "red"
    assert newest["channel"] == "sms"
    assert newest["threat_type"] != "none"
    assert newest["block_template"]
    # ES/EN: never message content
    assert "text" not in newest and "anonymized_text" not in newest


def test_newest_first(api_client, db_session, consented_solo):
    from datetime import UTC, datetime, timedelta

    from app.models.analysis import Analysis

    headers = consented_solo["headers"]
    old = analyze(api_client, headers, SAFE)
    new = analyze(api_client, headers, SAFE)
    row = db_session.get(Analysis, uuid.UUID(old))
    row.created_at = datetime.now(UTC) - timedelta(days=1)
    db_session.flush()

    data = api_client.get(MY_ANALYSES, headers=headers).json()
    assert [item["analysis_id"] for item in data["items"]] == [new, old]


def test_pagination(api_client, consented_solo):
    headers = consented_solo["headers"]
    ids = {analyze(api_client, headers, SAFE) for _ in range(3)}

    page = api_client.get(f"{MY_ANALYSES}?limit=2&offset=0", headers=headers).json()
    rest = api_client.get(f"{MY_ANALYSES}?limit=2&offset=2", headers=headers).json()
    assert page["total"] == rest["total"] == 3
    assert len(page["items"]) == 2 and len(rest["items"]) == 1
    seen = [i["analysis_id"] for i in page["items"] + rest["items"]]
    # ES/EN: same transaction in tests -> equal created_at; check no gaps/overlap
    assert set(seen) == ids and len(seen) == 3


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
def test_invalid_pagination(api_client, solo, query):
    response = api_client.get(f"{MY_ANALYSES}?{query}", headers=solo["headers"])
    assert response.status_code == 422


def test_does_not_show_other_users_analyses(
    api_client,
    consented_solo,
    consented_senior,
):
    body = analysis_body(PHISHING, device_id=consented_senior.device.id)
    api_client.post(ANALYSES, json=body, headers=consented_senior.headers)
    data = api_client.get(MY_ANALYSES, headers=consented_solo["headers"]).json()
    assert data["total"] == 0


def test_forbidden_for_other_roles(api_client, consented_senior, guardian_headers):
    for headers in (consented_senior.headers, guardian_headers):
        response = api_client.get(MY_ANALYSES, headers=headers)
        assert response.status_code == 403


def test_requires_token(api_client):
    assert api_client.get(MY_ANALYSES).status_code == 401
