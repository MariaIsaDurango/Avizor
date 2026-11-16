"""Tests de los endpoints de estadísticas (necesitan PostgreSQL).
Statistics endpoint tests (need PostgreSQL).
"""

import pytest


def test_daily_stats_returns_200_and_shape(api_client):
    response = api_client.get("/api/v1/stats/daily?period=7")
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 7
    assert isinstance(data["rows"], list)
    assert len(data["rows"]) == 7
    if data["rows"]:
        row = data["rows"][0]
        assert "date" in row
        assert "amber" in row
        assert "red" in row
        assert "green" not in row


def test_summary_stats_returns_200_and_shape(api_client):
    response = api_client.get("/api/v1/stats/summary?period=30")
    assert response.status_code == 200
    data = response.json()
    assert data["period_days"] == 30
    assert "total" in data
    assert isinstance(data["total"], int)
    assert "by_threat_type" in data
    assert "by_channel" in data


@pytest.mark.parametrize("path", [
    "/api/v1/stats/daily?period=15",
    "/api/v1/stats/summary?period=15",
    "/api/v1/stats/daily?period=0",
    "/api/v1/stats/daily?period=abc",
])
def test_invalid_period_returns_422(api_client, path):
    assert api_client.get(path).status_code == 422
