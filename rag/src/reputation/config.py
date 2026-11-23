"""All outbound services are opt-in; no secrets in source code."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Config:
    budget_ms: int = 350
    virustotal_key: str = field(default="", repr=False)
    google_key: str = field(default="", repr=False)
    numverify_key: str = field(default="", repr=False)
    allow_external_urls: bool = False
    allow_external_phones: bool = False

    def __post_init__(self):
        if not 1 <= self.budget_ms <= 350:
            raise ValueError("Budget must be 1–350 ms")

    @classmethod
    def from_env(cls):
        return cls(
            virustotal_key=os.getenv("AVIZOR_VT_KEY", ""),
            google_key=os.getenv("AVIZOR_GSB_KEY", ""),
            numverify_key=os.getenv("AVIZOR_NUMVERIFY_KEY", ""),
            allow_external_urls=os.getenv("AVIZOR_EXTERNAL_URLS") == "1",
            allow_external_phones=os.getenv("AVIZOR_EXTERNAL_PHONES") == "1",
        )
