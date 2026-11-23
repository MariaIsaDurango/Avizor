"""Read existing reports only. Never submit or scan an indicator."""

import base64

from rag.src.reputation.models import Signal
from rag.src.reputation.providers.common import Quota, request
from rag.src.reputation.validators import domain, url


class VirusTotal:
    name = "virustotal"
    kinds = ("url", "domain")

    def __init__(self, client, key):
        self.client = client
        self.key = key
        self.quota = Quota()

    async def check(self, kind, value):
        value = url(value) if kind == "url" else domain(value)
        if not self.quota.take():
            return Signal(self.name, "unavailable", reason="local_quota")
        path = (
            "urls/" + base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
            if kind == "url"
            else "domains/" + value
        )
        data = await request(
            self.client,
            self.name,
            "GET",
            "https://www.virustotal.com/api/v3/" + path,
            headers={"x-apikey": self.key},
        )
        if isinstance(data, Signal):
            return data
        try:
            stats = data["data"]["attributes"]["last_analysis_stats"]
            malicious, suspicious = stats["malicious"], stats["suspicious"]
            if (
                type(malicious) is not int
                or type(suspicious) is not int
                or min(malicious, suspicious) < 0
            ):
                raise ValueError("Invalid stats")
        except (KeyError, TypeError, ValueError):
            return Signal(self.name, "unavailable", reason="invalid_response")
        if malicious >= 2:
            return Signal(self.name, "malicious", 95, "multiple_engine_detections")
        if malicious or suspicious:
            return Signal(self.name, "suspicious", 60, "engine_detection")
        return Signal(self.name, "no_match", reason="no_positive_engine")
