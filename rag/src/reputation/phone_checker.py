"""Local indicator lookup uses backend-supplied HMAC; no cleartext storage."""

from rag.src.reputation.models import Signal
from rag.src.reputation.validators import phone


class LocalPhoneChecker:
    name = "local_phone"
    kinds = ("phone",)

    def __init__(self, hash_phone, reported_hashes):
        self.hash_phone = hash_phone
        self.reported_hashes = frozenset(reported_hashes)

    async def check(self, kind, value):
        if self.hash_phone(phone(value)) in self.reported_hashes:
            return Signal(self.name, "malicious", 95, "confirmed_local_indicator")
        return Signal(self.name, "unknown", reason="no_confirmed_local_indicator")


async def check_phone(service, value):
    return await service.check("phone", value)
