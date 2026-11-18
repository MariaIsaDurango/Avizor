"""Load an explicitly obtained local online-valid JSON snapshot at startup."""

import json
import time
from pathlib import Path

from rag.src.reputation.models import Signal
from rag.src.reputation.validators import url


class PhishTank:
    name = "phishtank"
    kinds = ("url",)

    def __init__(self, urls, loaded_at, max_age=86400, clock=time.time):
        self.urls = frozenset(urls)
        self.loaded_at = loaded_at
        self.max_age = max_age
        self.clock = clock

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        if path.stat().st_size > 100_000_000:
            raise ValueError("Snapshot too large")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise TypeError("Expected list")
        entries = set()
        for entry in data:
            if (
                not isinstance(entry, dict)
                or entry.get("verified") != "yes"
                or entry.get("online") != "yes"
            ):
                continue
            try:
                entries.add(url(entry["url"]))
            except (ValueError, TypeError, KeyError):
                continue
        return cls(entries, path.stat().st_mtime)

    async def check(self, kind, value):
        if not 0 <= self.clock() - self.loaded_at <= self.max_age:
            return Signal(self.name, "unavailable", reason="stale_snapshot")
        if url(value) in self.urls:
            return Signal(self.name, "malicious", 100, "verified_online_phishing")
        return Signal(self.name, "no_match", reason="not_in_snapshot")
