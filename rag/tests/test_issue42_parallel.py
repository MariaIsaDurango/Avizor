import asyncio
import time

from rag.scripts.validate_reputation_parallel import parallel_probe
from rag.src.reputation.models import Signal


class Stub:
    def __init__(self, name, kinds, target, status, score=None, delay=0):
        self.name, self.kinds, self.target = name, kinds, target
        self.status, self.score, self.delay = status, score, delay
        self.calls = []

    async def check(self, kind, value):
        self.calls.append((kind, value))
        assert (kind, value) == self.target
        await asyncio.sleep(self.delay)
        return Signal(self.name, self.status, self.score)


def test_parallel_probe_does_not_share_indicators_between_providers():
    local = Stub(
        "phishtank", ("url",), ("url", "https://phishing.example/"), "malicious", 100
    )
    remote = Stub(
        "virustotal",
        ("url", "domain"),
        ("domain", "example.com"),
        "no_match",
        delay=2,
    )
    google = Stub(
        "google_safe_browsing",
        ("url",),
        ("url", "https://example.org/"),
        "no_match",
        delay=2,
    )
    started = time.monotonic()
    report = asyncio.run(
        parallel_probe([(p, p.target) for p in (local, remote, google)])
    )
    assert time.monotonic() - started < 0.8
    assert len(report["signals"]) == 3
    assert report["signals"][0]["status"] == "malicious"
    assert all(s["reason"] == "deadline_exceeded" for s in report["signals"][1:])
    assert all(p.calls == [p.target] for p in (local, remote, google))
    assert "phishing.example" not in str(report)
