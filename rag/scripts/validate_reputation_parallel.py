"""Controlled concurrent live probe: never send a PhishTank URL to a remote API."""

import argparse
import asyncio
import json
import logging
import os
import sys
import warnings
from getpass import GetPassWarning, getpass
from pathlib import Path

import httpx
from dotenv import load_dotenv

from rag.scripts.validate_reputation_live import spanish_test_number
from rag.src.reputation.models import Signal
from rag.src.reputation.providers.numverify import Numverify
from rag.src.reputation.providers.phishtank import PhishTank
from rag.src.reputation.providers.safe_browsing import SafeBrowsing
from rag.src.reputation.providers.virustotal import VirusTotal
from rag.src.reputation.service import ReputationService

ROOT = Path(__file__).resolve().parents[2]


class TargetedProvider:
    """One explicitly chosen indicator per provider, no cross-provider disclosure."""

    def __init__(self, provider, indicator):
        self.provider = provider
        self.name = provider.name
        self.indicator = indicator
        self.kinds = (indicator[0],)

    async def check(self, kind, value):
        if (kind, value) != self.indicator:
            return Signal(self.name, "unknown", reason="not_targeted", ttl=0)
        return await self.provider.check(kind, value)


async def parallel_probe(targets):
    providers = [
        TargetedProvider(provider, indicator) for provider, indicator in targets
    ]
    indicators = list(dict.fromkeys(indicator for _, indicator in targets))
    result = await ReputationService(providers).check_many(indicators)
    expected = {
        (provider.name, indicators.index(indicator)) for provider, indicator in targets
    }
    selected = [
        s for s in result.signals if (s.provider, s.indicator_index) in expected
    ]
    # No values, exception details or credentials in the output.
    return {
        "mode": "parallel_fast_350ms",
        "elapsed_ms": round(result.elapsed_ms, 2),
        "within_400ms": result.elapsed_ms < 400,
        "signals": [
            {
                "provider": s.provider,
                "status": s.status,
                "score": s.score,
                "reason": s.reason,
            }
            for s in selected
        ],
    }


async def run(phone=None):
    feed = await asyncio.to_thread(
        PhishTank.from_file, ROOT / "rag/data/reputation/online-valid.json"
    )
    if not feed.urls:
        raise ValueError("Empty feed")
    vt_key = os.getenv("AVIZOR_VT_KEY")
    gsb_key = os.getenv("AVIZOR_GSB_KEY")
    if not vt_key or not gsb_key:
        raise ValueError("Missing URL provider key")
    async with httpx.AsyncClient(
        timeout=5, follow_redirects=False, trust_env=False
    ) as client:
        targets = [
            (feed, ("url", min(feed.urls))),
            (VirusTotal(client, vt_key), ("domain", "example.com")),
            (
                SafeBrowsing(client, gsb_key),
                ("url", "https://testsafebrowsing.appspot.com/"),
            ),
        ]
        if phone is not None:
            key = os.getenv("AVIZOR_NUMVERIFY_KEY")
            if not key:
                raise ValueError("Missing Numverify key")
            targets.append((Numverify(client, key), ("phone", phone)))
        report = await parallel_probe(targets)
    print(json.dumps(report))
    local_positive = any(
        s["provider"] == "phishtank" and s["status"] == "malicious"
        for s in report["signals"]
    )
    return int(not (local_positive and report["within_400ms"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized-phone", action="store_true")
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    load_dotenv(ROOT / ".env")
    phone = None
    try:
        if args.authorized_phone:
            if not sys.stdin.isatty() or not os.getenv("AVIZOR_NUMVERIFY_KEY"):
                raise ValueError("Interactive terminal and key required")
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                phone = spanish_test_number(
                    getpass("Own authorized Spanish test number (hidden): ")
                )
        return asyncio.run(run(phone))
    except (
        OSError,
        ValueError,
        TypeError,
        EOFError,
        ImportError,
        httpx.HTTPError,
        GetPassWarning,
    ) as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
