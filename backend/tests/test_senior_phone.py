"""Integration tests for PATCH /api/v1/senior/phone."""

PHONE = "/api/v1/senior/phone"
SENIOR = "/api/v1/senior"
SENIOR_ME = "/api/v1/senior/me"


def test_guardian_updates_phone(api_client, guardian_headers, paired_senior):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "+34 600 000 000"},
        headers=guardian_headers,
    )

    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "+34600000000"

    senior_profile = api_client.get(SENIOR_ME, headers=paired_senior.headers)
    assert senior_profile.status_code == 200
    assert senior_profile.json()["guardian_phone"] == "+34600000000"


def test_guardian_can_clear_phone(api_client, guardian_headers, paired_senior):
    api_client.patch(
        PHONE,
        json={"guardian_phone": "+34600000000"},
        headers=guardian_headers,
    )

    response = api_client.patch(
        PHONE,
        json={"guardian_phone": None},
        headers=guardian_headers,
    )

    assert response.status_code == 200
    assert response.json()["guardian_phone"] is None


def test_phone_is_normalized(api_client, guardian_headers, paired_senior):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "600 000 000"},
        headers=guardian_headers,
    )

    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "600000000"


def test_invalid_phone_is_rejected(api_client, guardian_headers, paired_senior):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "123"},
        headers=guardian_headers,
    )

    assert response.status_code == 422


def test_senior_cannot_update_guardian_phone(api_client, paired_senior):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "+34600000000"},
        headers=paired_senior.headers,
    )

    assert response.status_code == 403


def test_update_phone_requires_active_pairing(api_client, guardian_headers):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "+34600000000"},
        headers=guardian_headers,
    )

    assert response.status_code == 404


def test_update_phone_requires_authentication(api_client):
    response = api_client.patch(
        PHONE,
        json={"guardian_phone": "+34600000000"},
    )

    assert response.status_code == 401
