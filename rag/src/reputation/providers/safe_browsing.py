"""Explicit opt-in v4 Lookup adapter; sends the URL, not a hash."""

import re

from rag.src.reputation.models import Signal
from rag.src.reputation.providers.common import Quota, request
from rag.src.reputation.validators import url


class SafeBrowsing:
    name = "google_safe_browsing"
    kinds = ("url",)

    def __init__(self, client, key):
        self.client = client
        self.key = key
        self.quota = Quota(minute=4, day=100)

    async def check(self, kind, value):
        value = url(value)
        if not self.quota.take():
            return Signal(self.name, "unavailable", reason="local_quota")
        body = {
            "client": {"clientId": "avizor", "clientVersion": "0.1"},
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": value}],
            },
        }
        data = await request(
            self.client,
            self.name,
            "POST",
            "https://safebrowsing.googleapis.com/v4/threatMatches:find",
            params={"key": self.key},
            json=body,
        )
        if isinstance(data, Signal):
            return data
        if not data:
            return Signal(self.name, "no_match", reason="not_listed", ttl=0)
        matches = data.get("matches")
        if not isinstance(matches, list):
            return Signal(self.name, "unavailable", reason="invalid_response")
        if not matches:
            return Signal(self.name, "no_match", reason="not_listed", ttl=0)
        if not all(
            isinstance(m, dict) and isinstance(m.get("threatType"), str)
            for m in matches
        ):
            return Signal(self.name, "unavailable", reason="invalid_response")
        durations = [m.get("cacheDuration", "") for m in matches]
        if not all(
            isinstance(d, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]{1,9})?s", d)
            for d in durations
        ):
            return Signal(self.name, "unavailable", reason="invalid_cache_duration")
        return Signal(
            self.name,
            "malicious",
            95,
            "listed_threat",
            min(float(d[:-1]) for d in durations),
        )
