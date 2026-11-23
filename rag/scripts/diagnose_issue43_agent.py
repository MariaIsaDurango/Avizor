"""Local diagnostic with fictional messages; no DB writes or raw prompt logs."""

import argparse
import json
from time import monotonic

import httpx
from app.schemas.agent import AgentOutput

from rag.src.agent.graph import allowed_templates, output_from_selection, select_payload
from rag.src.agent.hybrid import HybridSelector
from rag.src.agent.llm import OllamaSelector
from rag.src.agent.retriever import Retriever
from rag.src.ingestion.pipeline import DEMO_PATH, resolve_official_path
from rag.src.vector_store.chroma_store import ChromaStore
from rag.src.vector_store.embeddings import E5Embedder


def emit(**data):
    print(json.dumps(data, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", action="store_true")
    parser.add_argument(
        "--model", choices=["gemma3:1b", "gemma3:4b"], default="gemma3:1b"
    )
    parser.add_argument(
        "--diagnostic", action="store_true", help="Use 40s diagnostic timeout, not SLA"
    )
    parser.add_argument(
        "--legacy", action="store_true", help="Compare original selector"
    )
    args = parser.parse_args()
    selector_class = OllamaSelector if args.legacy else HybridSelector
    budget = 40.0 if args.diagnostic else 10.0
    start = monotonic()
    embedder = E5Embedder()
    store = ChromaStore(
        resolve_official_path() if args.official else DEMO_PATH,
        revision=embedder.revision,
        synthetic=not args.official,
    )
    retriever = Retriever(store, embedder, demo=not args.official)
    emit(
        stage="startup",
        seconds=round(monotonic() - start, 3),
        model=args.model,
        mode="official" if args.official else "synthetic",
        llm_timeout=budget,
    )

    def received(response):
        response.read()
        try:
            data = response.json()
        except ValueError:
            emit(stage="http", status=response.status_code, json_valid=False)
            return
        metrics = {
            key: round(data[key] / 1e9, 3)
            for key in (
                "total_duration",
                "load_duration",
                "prompt_eval_duration",
                "eval_duration",
            )
            if isinstance(data.get(key), (int, float))
        }
        emit(
            stage="ollama",
            http_status=response.status_code,
            done=data.get("done"),
            done_reason=data.get("done_reason"),
            prompt_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            seconds=metrics,
        )

    text = (
        "Su cuenta bancaria ha sido bloqueada. Verifique sus datos urgentemente."
        if args.official
        else "SMS fraudulento de paquete retenido"
    )
    start = monotonic()
    stage = "retrieval"
    try:
        notices = retriever.retrieve(text, "smishing")
        emit(
            stage=stage,
            seconds=round(monotonic() - start, 3),
            count=len(notices),
            sources=[n.source for n in notices],
            distances=[round(n.distance, 4) for n in notices],
        )
        if not notices:
            emit(status="fallback", reason="no_notices")
            return
        state = {
            "text": text,
            "risk": "red",
            "threat": "smishing",
            "confidence": 0.9,
            "templates": allowed_templates("red", "smishing", "FAKE_DO_NOT_TOUCH"),
            "technical": [],
            "notices": notices,
        }
        stage = "llm"
        payload = select_payload(state)
        emit(stage="payload", characters=len(json.dumps(payload, ensure_ascii=False)))
        with httpx.Client(
            trust_env=False,
            follow_redirects=False,
            event_hooks={"response": [received]},
        ) as client:
            state["selection"] = selector_class(model=args.model, client=client).select(
                payload, timeout=budget
            )
        emit(
            stage="selection",
            references=state["selection"].references,
            block_template=state["selection"].block_template,
        )
        stage = "validation"
        output = AgentOutput.model_validate(output_from_selection(state))
        emit(
            status="enriched",
            elapsed_s=round(monotonic() - start, 3),
            evidence_count=len(output.evidence),
            within_15s=monotonic() - start < 15,
            diagnostic_only=True,
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic emits class only, not payload
        emit(
            status="fallback",
            failed_stage=stage,
            error_type=type(exc).__name__,
            elapsed_s=round(monotonic() - start, 3),
        )


if __name__ == "__main__":
    main()
