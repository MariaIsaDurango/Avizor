"""Offline smoke test; no API keys or real phishing URLs."""

import asyncio
import json
import time
from dataclasses import asdict

from rag.src.reputation.providers.phishtank import PhishTank
from rag.src.reputation.service import ReputationService, fast_path


async def main():
    provider = PhishTank(["https://phishing.example/login"], time.time())
    service = ReputationService([provider])

    async def classify():
        return {"risk_level": "amber", "threat_type": "smishing"}

    classification, reputation = await fast_path(
        classify, service, [("url", "https://phishing.example/login")]
    )
    print(
        json.dumps(
            {
                "mode": "synthetic",
                "classifier": classification,
                "score": reputation.score,
                **asdict(reputation),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
