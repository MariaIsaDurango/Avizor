"""Tests del formato de error RFC 9457 y de la app base.
Tests for the RFC 9457 error format and the base app.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import ApiError, register_error_handlers
from app.main import app
from app.schemas.enums import ErrorCode
from app.schemas.problem import ProblemDetail


class _Body(BaseModel):
    age: int


# ES: App aparte para no ensuciar la app real. EN: Separate app, real app untouched.
errors_app = FastAPI()
register_error_handlers(errors_app)


@errors_app.get("/_test/api-error")
def _api_error():
    raise ApiError(403, ErrorCode.CONSENT_MISSING, "Sin consentimiento vigente.")


@errors_app.get("/_test/http-404")
def _http_404():
    raise HTTPException(404, "Alerta no encontrada")


@errors_app.post("/_test/validation")
def _validation(body: _Body):
    return body


@errors_app.get("/_test/crash")
def _crash():
    raise RuntimeError("boom")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_client():
    return TestClient(errors_app, raise_server_exceptions=False)


def assert_problem(response, status: int, code: str):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    # ES: Valida contra el schema del contrato. EN: Validates against the contract schema.
    problem = ProblemDetail.model_validate(response.json())
    assert problem.code == code
    return problem


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-contract-version"] == "1.0.0"


def test_unknown_route_is_problem_404(client):
    problem = assert_problem(client.get("/nope"), 404, "NOT_FOUND")
    assert problem.detail == "Recurso no encontrado"


def test_http_exception_keeps_its_detail(test_client):
    problem = assert_problem(test_client.get("/_test/http-404"), 404, "NOT_FOUND")
    assert problem.detail == "Alerta no encontrada"


def test_api_error(test_client):
    assert_problem(test_client.get("/_test/api-error"), 403, "CONSENT_MISSING")


def test_validation_error_does_not_leak_values(test_client):
    response = test_client.post("/_test/validation", json={"age": "secret-value"})
    problem = assert_problem(response, 422, "VALIDATION_ERROR")
    assert "age" in problem.detail
    assert "secret-value" not in response.text


def test_unhandled_error_is_generic_500(test_client):
    response = test_client.get("/_test/crash")
    assert_problem(response, 500, "INTERNAL_ERROR")
    assert "boom" not in response.text


def test_cors_does_not_reflect_foreign_origins(client):
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers
