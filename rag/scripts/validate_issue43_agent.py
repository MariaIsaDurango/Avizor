"""Local integration smoke test with fictional messages, never user data."""

import argparse
import json
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from app.schemas.agent import AgentOutput
from app.schemas.verdict import Verdict

from rag.src.agent.graph import AgentEngine, allowed_templates, build_graph
from rag.src.agent.hybrid import HybridSelector
from rag.src.agent.llm import OllamaSelector
from rag.src.agent.retriever import Retriever
from rag.src.ingestion.pipeline import DEMO_PATH, resolve_official_path
from rag.src.vector_store.chroma_store import ChromaStore
from rag.src.vector_store.embeddings import E5Embedder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", action="store_true")
    parser.add_argument(
        "--model", choices=["gemma3:1b", "gemma3:4b"], default="gemma3:1b"
    )
    parser.add_argument(
        "--legacy", action="store_true", help="Compare original selector"
    )
    args = parser.parse_args()
    selector_class = OllamaSelector if args.legacy else HybridSelector
    embedder = E5Embedder()
    store = ChromaStore(
        resolve_official_path() if args.official else DEMO_PATH,
        revision=embedder.revision,
        synthetic=not args.official,
    )
    retriever = Retriever(store, embedder, demo=not args.official)
    graph = build_graph(retriever, selector_class(model=args.model))
    engine = AgentEngine(graph)
    cases = [
        "Su cuenta bancaria ha sido bloqueada. Verifique sus datos urgentemente."
        if args.official
        else "SMS fraudulento de paquete retenido",
        "Su banco informa de un acceso extraño. Confirme sus credenciales ahora."
        if args.official
        else "Su paquete está retenido. Confirme la dirección urgentemente.",
    ]
    try:
        for text in cases:
            start = monotonic()
            output = engine.analyze(
                {
                    "text": text,
                    "risk": "red",
                    "threat": "smishing",
                    "confidence": 0.9,
                    "templates": allowed_templates(
                        "red", "smishing", "FAKE_DO_NOT_TOUCH"
                    ),
                    "technical": [],
                }
            )
            if output:
                # Validate the actual backend contract; this is a preview, not a DB write.
                validated = AgentOutput.model_validate(output)
                Verdict(
                    analysis_id=uuid4(),
                    phase="agent",
                    risk_level=validated.risk_level,
                    threat_type=validated.threat_type,
                    action="block_and_alert",
                    block_template=validated.block_template,
                    confidence=validated.confidence,
                    final=True,
                    issued_at=datetime.now(UTC),
                )
            print(
                json.dumps(
                    {
                        "elapsed_s": round(monotonic() - start, 3),
                        "status": "enriched" if output else "fallback",
                        "output": output,
                    },
                    ensure_ascii=False,
                )
            )
    finally:
        engine.close()


if __name__ == "__main__":
    main()
