"""OpenSpam (api.openspam.es): community reports of Spanish spam numbers (#168).

Explicit privacy opt-in only: the number travels in the request URL (HTTPS),
so the backend enables this provider only with AVIZOR_EXTERNAL_PHONES=1.
Free keys are for non-commercial use only (OpenSpam terms).
"""

import time
from collections import deque
from urllib.parse import quote

import httpx

from rag.src.reputation.cache import TTLCache
from rag.src.reputation.models import Signal
from rag.src.reputation.providers.common import request
from rag.src.reputation.validators import phone

ENDPOINT = "https://api.openspam.es/api/number/"
DAY = 86400.0
# Free standard plan: 2 s between requests, 20/hour, 50/day (account limits).
MIN_INTERVAL = 2.0
PER_HOUR = 20
PER_DAY = 50
# The caller may stop waiting earlier; the request can still finish and fill
# the cache, so a slow answer does not spend the daily quota twice.
REQUEST_TIMEOUT = 3.0
# Stored danger level -> (status, policy score 0-100). Not a probability.
# Backend thresholds: >= 40 amber, >= 70 red. Any reported number is at least
# amber (#168: "a known spam number returns amber or red").
LEVELS = {
    "bajo": ("suspicious", 40),  # amber
    "medio": ("suspicious", 60),  # amber
    "alto": ("malicious", 85),  # red
    "muy_alto": ("malicious", 95),  # red
}


class _Limiter:
    def __init__(self, clock):
        self.clock = clock
        self.calls = deque()

    def take(self) -> bool:
        now = self.clock()
        while self.calls and now - self.calls[0] >= DAY:
            self.calls.popleft()
        if self.calls and now - self.calls[-1] < MIN_INTERVAL:
            return False
        if len(self.calls) >= PER_DAY:
            return False
        if sum(now - t < 3600 for t in self.calls) >= PER_HOUR:
            return False
        self.calls.append(now)
        return True


class OpenSpam:
    name = "openspam"
    kinds = ("phone",)

    def __init__(self, client, key, clock=time.monotonic):
        self.client = client
        self.key = key
        self.limiter = _Limiter(clock)
        # In-memory only, opaque HMAC keys, 24 h (issue #168). Never on disk.
        self.cache = TTLCache(max_entries=512, clock=clock)

    async def check(self, kind, value):
        value = phone(value)
        if not value.startswith("+34"):
            return Signal(self.name, "unknown", reason="not_spanish_number", ttl=0)
        key = self.cache.key(self.name, kind, value)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        if not self.limiter.take():
            return Signal(self.name, "unavailable", reason="local_quota", ttl=0)
        data = await request(
            self.client,
            self.name,
            "GET",
            ENDPOINT + quote(value, safe="+"),
            headers={"X-API-Key": self.key},
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
        )
        signal = self._parse(data)
        if signal.status in ("malicious", "suspicious", "no_match"):
            self.cache.put(key, signal, DAY)
        return signal

    def _parse(self, data):
        if isinstance(data, Signal):
            if data.reason == "report_not_found":
                return Signal(self.name, "no_match", reason="not_reported", ttl=DAY)
            return data
        payload = data.get("data")
        if data.get("success") is not True or not isinstance(payload, dict):
            return Signal(self.name, "unavailable", reason="invalid_response", ttl=0)
        found = payload.get("encontrado")
        if found is False:
            return Signal(self.name, "no_match", reason="not_reported", ttl=DAY)
        number = payload.get("numero")
        if found is not True or not isinstance(number, dict):
            return Signal(self.name, "unavailable", reason="invalid_response", ttl=0)
        level = number.get("nivel_peligro")
        status, score = LEVELS.get(level, ("suspicious", 50))
        reason = f"level_{level}" if level in LEVELS else "level_unknown"
        return Signal(self.name, status, score, reason, ttl=DAY)
