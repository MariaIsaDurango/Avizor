"""Tests del portal web: comprueba que las cuatro páginas responden 200.
Web portal tests: checks that the four pages return 200.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def web_client():
    # ES: Las rutas web no usan BD, no hace falta db_session.
    # EN: Web routes don't use the DB, db_session is not needed.
    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.mark.parametrize("path", ["/", "/analytics", "/indicators", "/support"])
def test_web_page_returns_200(web_client, path):
    response = web_client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
