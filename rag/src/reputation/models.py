"""Internal signals, not calibrated probabilities or final verdicts."""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["url", "domain", "phone"]
Status = Literal[
    "malicious", "suspicious", "no_match", "unknown", "unavailable", "valid", "invalid"
]


@dataclass(frozen=True, slots=True)
class Signal:
    provider: str
    status: Status
    score: int | None = None
    reason: str = ""
    ttl: float = 60
    indicator_index: int | None = None


@dataclass(frozen=True, slots=True)
class ReputationResult:
    signals: tuple[Signal, ...]
    elapsed_ms: float

    @property
    def score(self) -> int | None:
        return max((s.score for s in self.signals if s.score is not None), default=None)

    @property
    def actionable(self) -> bool:
        return any(
            s.status in ("malicious", "suspicious") and s.score is not None
            for s in self.signals
        )
