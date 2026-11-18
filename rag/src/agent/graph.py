"""Bounded LangGraph enrichment. A failed graph yields no agent verdict."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Lock
from time import monotonic
from typing import TypedDict

from .evidence import official_evidence
from .llm import Selection
from .retriever import RetrievedNotice


class State(TypedDict, total=False):
    text: str
    risk: str
    threat: str
    confidence: float
    templates: list[str]
    technical: list[dict]
    deadline: float
    notices: list[RetrievedNotice]
    selection: Selection
    output: dict


TEMPLATES = {
    "green": ["UNSURE_CALL_FAMILY"],
    "amber": ["UNSURE_CALL_FAMILY", "FAKE_DO_NOT_TOUCH"],
    "red": ["FAKE_DO_NOT_TOUCH"],
}


def allowed_templates(risk: str, threat: str, baseline: str) -> list[str]:
    values = list(TEMPLATES[risk])
    if risk != "green":
        if threat == "vishing":
            values.append("SUSPICIOUS_CALL")
        if baseline in {"DANGEROUS_LINK", "ASKS_BANK_DETAILS"}:
            values.append(baseline)
    return values


def remaining(state: State) -> float:
    budget = state["deadline"] - monotonic()
    if budget <= 0:
        raise TimeoutError("Agent deadline")
    return budget


def select_payload(state: State) -> dict:
    # Explicit compact excerpt budget. Retrieval still uses full E5 fragments.
    # No raw URL list or arbitrary technical values sent to the model.
    notices = [
        {"index": i, "title": n.title[:180], "excerpt": n.text[:320]}
        for i, n in enumerate(state["notices"])
    ]
    return {
        "anonymized_text": state["text"],
        "fast_risk_level": state["risk"],
        "fast_threat_type": state["threat"],
        "allowed_templates": state["templates"],
        "notices": notices,
    }


def output_from_selection(state: State) -> dict:
    selection = state["selection"]
    if selection.block_template not in state["templates"]:
        raise ValueError("Invalid template")
    indices = selection.references
    if (
        not indices
        or len(set(indices)) != len(indices)
        or any(i < 0 or i >= len(state["notices"]) for i in indices)
    ):
        raise ValueError("Invalid references")
    selected = [state["notices"][i] for i in indices]
    official = official_evidence(selected)
    technical = state["technical"][:5]
    # Preserve at least one official reference if available; no model-authored URLs.
    evidence = technical[:4] + official if official else technical
    explanation = (
        "La vía rápida ha identificado señales de riesgo. "
        "Se han seleccionado avisos oficiales sobre patrones relacionados; "
        "no demuestran por sí solos que este mensaje sea fraudulento."
        if official
        else "La vía rápida ha identificado señales de riesgo. Consulta a tu tutor."
    )
    return {
        "risk_level": state["risk"],
        "threat_type": state["threat"],
        "block_template": selection.block_template,
        "confidence": state["confidence"],
        "explanation": explanation,
        "evidence": evidence[:5],
    }


def build_graph(retriever, selector):
    from langgraph.graph import END, START, StateGraph

    def retrieve(state: State):
        remaining(state)
        return {"notices": retriever.retrieve(state["text"], state["threat"])[:5]}

    def choose(state: State):
        budget = min(10.0, remaining(state))
        selection = selector.select(select_payload(state), timeout=budget)
        remaining(state)
        return {"selection": Selection.model_validate(selection)}

    def validate(state: State):
        remaining(state)
        return {"output": output_from_selection(state)}

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("choose", choose)
    graph.add_node("validate", validate)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        lambda s: "choose" if s["notices"] else "end",
        {"choose": "choose", "end": END},
    )
    graph.add_edge("choose", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


class AgentEngine:
    """One worker per runtime. A late task cannot publish a verdict."""

    def __init__(self, graph, *, timeout: float = 13.0):
        if not 0 < timeout <= 13:
            raise ValueError("Invalid agent timeout")
        self.graph = graph
        self.timeout = timeout
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.slot = Lock()

    def close(self):
        self.pool.shutdown(wait=False, cancel_futures=True)

    def _invoke(self, state: State) -> dict:
        # LangGraph depends on LangSmith; explicitly disable tracing of messages.
        from langsmith import tracing_context

        with tracing_context(enabled=False):
            return self.graph.invoke(state)

    def analyze(self, state: State) -> dict | None:
        if (
            not state["text"].strip()
            or len(state["text"]) > 1200
            or state["threat"] == "none"
            or state["risk"] == "green"
        ):
            return None
        start = monotonic()
        if not self.slot.acquire(blocking=False):
            return None
        try:
            future = self.pool.submit(
                self._invoke,
                {
                    **{
                        key: state[key]
                        for key in (
                            "text",
                            "risk",
                            "threat",
                            "confidence",
                            "templates",
                            "technical",
                        )
                    },
                    "deadline": start + self.timeout,
                },
            )
        except RuntimeError:
            self.slot.release()
            return None
        future.add_done_callback(lambda _: self.slot.release())
        try:
            result = future.result(timeout=max(0, self.timeout - (monotonic() - start)))
            if monotonic() - start >= self.timeout:
                return None
            return result.get("output")
        except Exception:  # noqa: BLE001 - do not log untrusted text or model errors
            future.cancel()
            return None
