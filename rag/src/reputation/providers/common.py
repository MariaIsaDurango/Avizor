"""Process-local quota limiter and fixed-endpoint HTTPS requests."""

import time
from collections import deque

import httpx

from rag.src.reputation.models import Signal


class Quota:
    def __init__(self, minute=4, day=500, clock=time.monotonic):
        self.minute = minute
        self.day = day
        self.clock = clock
        self.calls = deque()

    def take(self):
        now = self.clock()
        while self.calls and now - self.calls[0] >= 86400:
            self.calls.popleft()
        if (
            len(self.calls) >= self.day
            or sum(now - t < 60 for t in self.calls) >= self.minute
        ):
            return False
        self.calls.append(now)
        return True


async def request(client, provider, method, endpoint, **kwargs):
    try:
        response = await client.request(
            method, endpoint, follow_redirects=False, **kwargs
        )
        if response.status_code == 404:
            return Signal(provider, "unknown", reason="report_not_found")
        if response.status_code != 200:
            return Signal(
                provider, "unavailable", reason=f"http_{response.status_code}"
            )
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("Invalid response")
        return data
    except (httpx.HTTPError, ValueError, TypeError):
        return Signal(provider, "unavailable", reason="request_failed")
