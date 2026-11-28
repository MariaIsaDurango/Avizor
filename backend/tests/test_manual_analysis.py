"""Tests del reenvío manual multimodal (202 + agente) y del sondeo del veredicto.
Multimodal manual forward (202 + agent) and verdict polling tests.

ES: La tarea en segundo plano se sustituye por una lista (fixture "jobs") y se
    ejecuta a mano con db_session, para que todo quede dentro del rollback.
EN: The background task is replaced by a list ("jobs" fixture) and run by
    hand with db_session, so everything stays inside the rollback.
"""

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from time import monotonic

import pytest
from sqlalchemy import select

from app.api import manual_form
from app.models.alert import Alert
from app.models.analysis import Analysis, AnalysisAttachment, TempContent
from app.models.indicator import Indicator
from app.schemas.enums import InputType
from app.services import manual_analysis as manual_service
from app.services.extraction import IMAGE_ENGINE
from app.services.manual_analysis import finish_manual_analysis

ANALYSES = "/api/v1/analyses"
PHISHING = "BBVA: su cuenta [IBAN] ha sido bloqueada. Verifique en https://bbva-seguro.top/login"
FAMILY = "Hola, ¿comemos el domingo en casa?"
JPEG = b"\xff\xd8\xff" + b"0" * 2048


@pytest.fixture
def jobs(monkeypatch):
    calls: list[manual_service.ManualJob] = []
    monkeypatch.setattr(manual_service, "run_manual_job", calls.append)
    return calls


@pytest.fixture
def fake_ocr(monkeypatch):
    def use(text: str) -> None:
        monkeypatch.setitem(
            manual_service.SERVER_EXTRACTORS,
            InputType.IMAGE,
            (lambda _data: text, IMAGE_ENGINE),
        )

    return use


def metadata(senior, text=PHISHING, attachments=(), applied=True):
    return {
        "device_id": str(senior.device.id),
        "channel": "manual",
        "origin": "manual",
        "received_at": "2026-11-16T13:30:00Z",
        "text": text,
        "anonymization": {"applied": applied, "ner_model_version": "ner-test"},
        "attachments": list(attachments),
    }


def image(ocr_text=None, ner_applied=True, field="attachment_0"):
    local = None
    if ocr_text is not None:
        local = {"ocr": True, "extracted_text": ocr_text, "ner_applied": ner_applied}
    return {
        "file_field": field,
        "type": "image",
        "mime": "image/jpeg",
        "size_bytes": len(JPEG),
        "local_preprocessing": local,
    }


def send(client, senior, meta, files=None):
    parts = {"metadata": (None, json.dumps(meta), "application/json")}
    parts.update(files or {})
    return client.post(ANALYSES, files=parts, headers=senior.headers)


def jpeg_file(field="attachment_0"):
    return {field: ("captura.jpg", JPEG, "image/jpeg")}


def poll(client, senior, analysis_id):
    return client.get(f"{ANALYSES}/{analysis_id}/verdict", headers=senior.headers)


# ---------- POST multipart → 202 ----------


def test_manual_forward_returns_202(api_client, db_session, paired_senior, jobs):
    response = send(api_client, paired_senior, metadata(paired_senior))
    assert response.status_code == 202
    body = response.json()
    assert body["retry_after_ms"] == manual_service.RETRY_AFTER_MS
    analysis = db_session.get(Analysis, uuid.UUID(body["analysis_id"]))
    assert analysis.final is False
    assert len(jobs) == 1


def test_nothing_is_stored_before_the_agent(
    api_client, db_session, paired_senior, jobs
):
    """ES: Sin veredicto final: ni texto, ni alertas. EN: No final verdict yet."""
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    analysis_id = uuid.UUID(body["analysis_id"])
    assert db_session.get(TempContent, analysis_id) is None
    assert (
        db_session.scalars(select(Alert).where(Alert.analysis_id == analysis_id)).all()
        == []
    )


def test_poll_while_pending_returns_202(api_client, paired_senior, jobs):
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    response = poll(api_client, paired_senior, body["analysis_id"])
    assert response.status_code == 202
    assert response.json()["analysis_id"] == body["analysis_id"]


# ---------- Agente / agent ----------


def test_disabled_rag_red_creates_alert_and_final_verdict(
    api_client, db_session, paired_senior, jobs
):
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    alert_ids = finish_manual_analysis(db_session, jobs[0])

    response = poll(api_client, paired_senior, body["analysis_id"])
    assert response.status_code == 200
    verdict = response.json()
    assert verdict["phase"] == "fast"
    assert verdict["final"] is True
    assert verdict["risk_level"] == "red"
    assert verdict["action"] == "block_and_alert"
    assert len(alert_ids) == 1
    stored = db_session.get(TempContent, uuid.UUID(body["analysis_id"]))
    assert "[IBAN]" in stored.anonymized_text


def test_agent_green_stores_no_text(api_client, db_session, paired_senior, jobs):
    body = send(api_client, paired_senior, metadata(paired_senior, text=FAMILY)).json()
    assert finish_manual_analysis(db_session, jobs[0]) == []
    verdict = poll(api_client, paired_senior, body["analysis_id"]).json()
    assert verdict["risk_level"] == "green"
    assert verdict["block_template"] in {"LOOKS_SAFE", "UNSURE_CALL_FAMILY"}
    assert db_session.get(TempContent, uuid.UUID(body["analysis_id"])) is None


def test_finishing_twice_does_nothing(api_client, db_session, paired_senior, jobs):
    send(api_client, paired_senior, metadata(paired_senior))
    assert len(finish_manual_analysis(db_session, jobs[0])) == 1
    assert finish_manual_analysis(db_session, jobs[0]) == []


class BadAgent:
    model_version = "bad-agent"

    def analyze(self, data):
        # ES: Intento de inyección: campos inventados. EN: Injection attempt.
        return {"risk_level": "green", "action": "allow", "say_to_senior": "todo ok"}


class BrokenAgent:
    model_version = "broken-agent"

    def analyze(self, data):
        raise TimeoutError("LLM caído")


@pytest.mark.parametrize("agent", [BadAgent(), BrokenAgent()])
def test_invalid_agent_falls_back_to_fast_path(
    api_client, db_session, paired_senior, jobs, monkeypatch, agent
):
    monkeypatch.setattr(manual_service, "get_agent", lambda fast, **kwargs: agent)
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    finish_manual_analysis(db_session, jobs[0])
    verdict = poll(api_client, paired_senior, body["analysis_id"]).json()
    assert verdict["phase"] == "fast"
    assert verdict["risk_level"] == "red"


def test_agent_timeout_closes_with_fast_path(
    api_client, db_session, paired_senior, jobs
):
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    analysis = db_session.get(Analysis, uuid.UUID(body["analysis_id"]))
    analysis.created_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.flush()

    response = poll(api_client, paired_senior, body["analysis_id"])
    assert response.status_code == 200
    assert response.json()["phase"] == "fast"
    assert db_session.scalars(
        select(Alert).where(Alert.analysis_id == analysis.id)
    ).all()


class InventingAgent:
    """ES: Devuelve un "dominio" que no está en el mensaje (inyección HTML).
    EN: Returns a "domain" that is not in the message (HTML injection).
    """

    model_version = "inventing-agent"

    def analyze(self, data):
        return {
            "risk_level": "red",
            "threat_type": data.fast_threat_type,
            "block_template": "FAKE_DO_NOT_TOUCH",
            "confidence": 0.9,
            "explanation": "Suplanta a un banco.",
            "evidence": [
                {
                    "type": "domain",
                    "value": "<img src=x onerror=alert(1)>",
                    "reason": "x",
                },
                {
                    "type": "domain",
                    "value": "bbva-seguro.top",
                    "reason": "Dominio falso.",
                },
            ],
        }


def test_agent_cannot_invent_indicators(
    api_client, db_session, paired_senior, jobs, monkeypatch
):
    monkeypatch.setattr(
        manual_service, "get_agent", lambda fast, **kwargs: InventingAgent()
    )
    send(api_client, paired_senior, metadata(paired_senior))
    alert_ids = finish_manual_analysis(db_session, jobs[0])
    assert len(alert_ids) == 1
    alert = db_session.get(Alert, alert_ids[0])
    assert all("<" not in item.get("value", "") for item in alert.evidence)
    values = set(db_session.scalars(select(Indicator.public_value)).all())
    assert "bbva-seguro.top" in values
    assert not any("<" in value for value in values)


# ---------- Adjuntos / attachments ----------


def test_device_ocr_text_is_analyzed(api_client, db_session, paired_senior, jobs):
    meta = metadata(paired_senior, text=None, attachments=[image(ocr_text=PHISHING)])
    body = send(api_client, paired_senior, meta, jpeg_file()).json()
    finish_manual_analysis(db_session, jobs[0])
    assert (
        poll(api_client, paired_senior, body["analysis_id"]).json()["risk_level"]
        == "red"
    )

    row = db_session.scalars(
        select(AnalysisAttachment).where(
            AnalysisAttachment.analysis_id == uuid.UUID(body["analysis_id"])
        )
    ).one()
    assert row.ner_applied_on == "device"
    assert row.extraction_engine == "device-ocr"
    assert row.size_bytes == len(JPEG)


def test_attachment_without_preprocessing_is_server_processed(
    api_client, db_session, paired_senior, jobs, fake_ocr
):
    fake_ocr("Texto extraído por el servidor")
    meta = metadata(paired_senior, text=None, attachments=[image()])
    body = send(api_client, paired_senior, meta, jpeg_file()).json()
    analysis = db_session.get(Analysis, uuid.UUID(body["analysis_id"]))
    assert analysis.server_processed is True


def test_ocr_without_ner_is_rejected(api_client, paired_senior, jobs):
    meta = metadata(
        paired_senior,
        text=None,
        attachments=[image(ocr_text="Hola", ner_applied=False)],
    )
    response = send(api_client, paired_senior, meta, jpeg_file())
    assert response.status_code == 422
    assert response.json()["code"] == "CONTENT_NOT_ANONYMIZED"
    assert jobs == []


def test_text_not_anonymized_is_rejected(api_client, paired_senior, jobs):
    response = send(api_client, paired_senior, metadata(paired_senior, applied=False))
    assert response.status_code == 422
    assert response.json()["code"] == "CONTENT_NOT_ANONYMIZED"


def test_declared_file_must_be_sent(api_client, paired_senior, jobs):
    meta = metadata(paired_senior, attachments=[image(ocr_text="Hola")])
    assert send(api_client, paired_senior, meta).status_code == 422


def test_undeclared_file_is_rejected(api_client, paired_senior, jobs):
    response = send(api_client, paired_senior, metadata(paired_senior), jpeg_file())
    assert response.status_code == 422


def test_invalid_metadata_names_the_field(api_client, paired_senior, jobs):
    response = send(api_client, paired_senior, metadata(paired_senior, text=None))
    assert response.status_code == 422
    assert "metadata" in response.json()["detail"]


def test_too_large_request_is_413(api_client, paired_senior, jobs, monkeypatch):
    monkeypatch.setattr(manual_form, "MAX_REQUEST_BYTES", 1024)
    meta = metadata(paired_senior, attachments=[image(ocr_text="Hola")])
    assert send(api_client, paired_senior, meta, jpeg_file()).status_code == 413


def test_files_are_kept_in_memory():
    """ES: Nunca a disco (contrato). EN: Never to disk (contract)."""
    assert (
        manual_form.InMemoryMultiPartParser.spool_max_size
        >= manual_form.MAX_REQUEST_BYTES
    )


# ---------- Permisos / permissions ----------


def test_other_device_id_is_forbidden(api_client, paired_senior, jobs):
    meta = metadata(paired_senior)
    meta["device_id"] = str(uuid.uuid4())
    assert send(api_client, paired_senior, meta).status_code == 403


def test_guardian_cannot_send(api_client, paired_senior, guardian_headers, jobs):
    parts = {
        "metadata": (None, json.dumps(metadata(paired_senior)), "application/json")
    }
    response = api_client.post(ANALYSES, files=parts, headers=guardian_headers)
    assert response.status_code == 403


def test_unknown_verdict_is_404(api_client, paired_senior):
    assert poll(api_client, paired_senior, uuid.uuid4()).status_code == 404


# ---------- La vía rápida en JSON sigue igual / JSON fast path unchanged ----------


def test_fast_path_verdict_can_be_polled(api_client, consented_senior):
    body = {
        "device_id": str(consented_senior.device.id),
        "channel": "sms",
        "origin": "automatic",
        "input_type": "text",
        "received_at": "2026-11-16T13:30:00Z",
        "content": {
            "text": PHISHING,
            "urls": ["https://bbva-seguro.top/login"],
            "anonymization": {"applied": True, "ner_model_version": "ner-test"},
        },
    }
    verdict = api_client.post(
        ANALYSES, json=body, headers=consented_senior.headers
    ).json()
    polled = poll(api_client, consented_senior, verdict["analysis_id"]).json()
    assert polled["phase"] == "fast"
    assert polled["risk_level"] == verdict["risk_level"]


def test_rag_evidence_persisted_only_for_guardian(
    api_client, db_session, paired_senior, jobs, monkeypatch
):
    from app.services import agent as rag_service

    url = "https://www.incibe.es/ciudadania/avisos/campana-de-smishing-que-suplanta-entidades-bancarias-solicitando-que-les-llames"

    class Engine:
        def analyze(self, state, *, timeout):
            assert "[IBAN]" in state["text"]
            assert 0 < timeout <= 13
            return {
                "risk_level": state["risk"],
                "threat_type": state["threat"],
                "confidence": state["confidence"],
                "block_template": "FAKE_DO_NOT_TOUCH",
                "explanation": "Aviso oficial relacionado.",
                "evidence": state["technical"]
                + [{"type": "official_notice", "source": "incibe", "url": url}],
            }

    monkeypatch.setattr(rag_service, "_engine", Engine())
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    ids = finish_manual_analysis(db_session, jobs[0])
    assert len(ids) == 1
    verdict = poll(api_client, paired_senior, body["analysis_id"]).json()
    assert verdict["phase"] == "agent"
    assert verdict["risk_level"] == "red"
    assert "explanation" not in verdict and "evidence" not in verdict
    alert = db_session.get(Alert, ids[0])
    assert any(item.get("url") == url for item in alert.evidence)
    assert db_session.get(Analysis, uuid.UUID(body["analysis_id"])).latency_ms >= 0
    assert finish_manual_analysis(db_session, jobs[0]) == []


def test_late_agent_cannot_overwrite_expired_verdict(
    api_client, db_session, paired_senior, jobs, monkeypatch
):
    class LateAgent:
        model_version = "late-test"

        def analyze(self, data):
            # Simulate a poll winning finalization while the agent is in flight.
            row = db_session.get(Analysis, jobs[0].analysis_id)
            row.created_at = datetime.now(UTC) - timedelta(seconds=20)
            db_session.flush()
            manual_service._expire(db_session, row.id)
            return {
                "risk_level": data.fast_risk_level,
                "threat_type": data.fast_threat_type,
                "block_template": "FAKE_DO_NOT_TOUCH",
                "confidence": 0.9,
                "explanation": "Late agent",
                "evidence": [],
            }

    monkeypatch.setattr(manual_service, "get_agent", lambda fast, **kwargs: LateAgent())
    body = send(api_client, paired_senior, metadata(paired_senior)).json()
    assert finish_manual_analysis(db_session, jobs[0]) == []
    verdict = poll(api_client, paired_senior, body["analysis_id"]).json()
    assert verdict["phase"] == "fast"
    assert (
        len(
            db_session.scalars(
                select(Alert).where(Alert.analysis_id == jobs[0].analysis_id)
            ).all()
        )
        == 1
    )


@pytest.mark.skipif(
    os.environ.get("AVIZOR_RUN_LIVE_RAG_TEST") != "1",
    reason="Opt-in: needs local official corpus, E5, Ollama and PostgreSQL",
)
def test_live_rag_manual_endpoint(api_client, db_session, paired_senior, jobs):
    from app.services import agent as rag_service

    start = monotonic()
    rag_service.initialize_agent(True)
    print(f"RAG startup: {monotonic() - start:.3f} s")
    try:
        assert rag_service._engine is not None, "RAG not initialized"
        start = monotonic()
        text = "SMS de mi banco: su cuenta ha sido bloqueada. Verifique sus claves urgentemente."
        response = send(api_client, paired_senior, metadata(paired_senior, text=text))
        assert response.status_code == 202
        ids = finish_manual_analysis(db_session, jobs[0])
        final = poll(api_client, paired_senior, response.json()["analysis_id"])
        elapsed = monotonic() - start
        assert final.status_code == 200
        verdict = final.json()
        print(
            json.dumps(
                {
                    "elapsed_s": round(elapsed, 3),
                    "phase": verdict["phase"],
                    "risk": verdict["risk_level"],
                    "threat": verdict["threat_type"],
                }
            )
        )
        assert elapsed < 15
        assert verdict["risk_level"] == "red"
        assert verdict["phase"] == "agent"
        assert "evidence" not in verdict and "explanation" not in verdict
        assert len(ids) == 1
        alert = db_session.get(Alert, ids[0])
        evidence = [
            item for item in alert.evidence if item["type"] == "official_notice"
        ]
        print(json.dumps({"official_evidence": evidence}, ensure_ascii=False))
        assert evidence
    finally:
        rag_service.close_agent()
