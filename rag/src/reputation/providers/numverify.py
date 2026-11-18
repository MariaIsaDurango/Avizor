"""Number validity is not fraud reputation. Explicit privacy opt-in only."""

from rag.src.reputation.models import Signal
from rag.src.reputation.providers.common import Quota, request
from rag.src.reputation.validators import phone


class Numverify:
    name = "numverify"
    kinds = ("phone",)

    def __init__(self, client, key):
        self.client = client
        self.key = key
        self.quota = Quota(minute=1, day=3)

    async def check(self, kind, value):
        value = phone(value)
        if not self.quota.take():
            return Signal(self.name, "unavailable", reason="local_quota")
        data = await request(
            self.client,
            self.name,
            "GET",
            "https://api.apilayer.net/numverify/validate",
            params={
                "access_key": self.key,
                "number": value,
                "format": 1,
                **({"country_code": "ES"} if value.startswith("+34") else {}),
            },
        )
        if isinstance(data, Signal):
            return data
        if type(data.get("valid")) is not bool:
            return Signal(self.name, "unavailable", reason="invalid_response")
        return Signal(
            self.name,
            "valid" if data["valid"] else "invalid",
            reason="number_validation_only",
        )
