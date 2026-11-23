"""Explicit, bounded probes; never connect to an indicator host."""

import argparse
import asyncio
import bz2
import hashlib
import json
import logging
import os
import re
import sys
import tempfile
import time
import warnings
from contextlib import contextmanager
from getpass import GetPassWarning, getpass
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from rag.src.reputation.config import Config
from rag.src.reputation.providers.numverify import Numverify
from rag.src.reputation.providers.phishtank import PhishTank
from rag.src.reputation.providers.safe_browsing import SafeBrowsing
from rag.src.reputation.providers.virustotal import VirusTotal
from rag.src.reputation.service import ReputationService

FEED = Path("rag/data/reputation/online-valid.json")
MAX_BYTES = 100_000_000


@contextmanager
def feed_response(client, endpoint):
    headers = {
        "User-Agent": "phishtank/avizor-educational",
        "Cache-Control": "no-cache",
    }
    with client.stream("GET", endpoint, headers=headers) as response:
        if response.status_code not in (301, 302, 303, 307, 308):
            yield response
            return
        location = response.headers.get("location", "")
        target = urlsplit(location)
        if (
            target.scheme != "https"
            or target.netloc.lower() != "cdn.phishtank.com"
            or not re.fullmatch(
                r"/datadumps/[A-Za-z0-9_-]+\.json(?:\.bz2)?", target.path
            )
            or target.fragment
        ):
            raise ValueError("Unapproved feed redirect")
    # One redirect only; do not forward cookies from the first host.
    client.cookies.clear()
    with client.stream("GET", location, headers=headers) as response:
        yield response


def download():
    key = os.getenv("AVIZOR_PHISHTANK_KEY", "")
    if key and not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError("Invalid application key format")
    endpoint = (
        "https://data.phishtank.com/data/"
        + (key + "/" if key else "")
        + "online-valid.json.bz2"
    )
    FEED.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with (
            httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client,
            feed_response(client, endpoint) as response,
        ):
            if response.status_code != 200:
                print(
                    json.dumps(
                        {"download": "failed", "http_status": response.status_code}
                    )
                )
                return 1
            decoder = None
            first = True
            size = compressed = 0
            started = time.monotonic()
            with tempfile.NamedTemporaryFile(dir=FEED.parent, delete=False) as out:
                temp = Path(out.name)
                for block in response.iter_bytes(chunk_size=65536):
                    compressed += len(block)
                    if compressed > MAX_BYTES or time.monotonic() - started > 120:
                        raise ValueError("Download limit exceeded")
                    if first:
                        decoder = (
                            bz2.BZ2Decompressor() if block.startswith(b"BZh") else None
                        )
                        first = False
                    data = (
                        decoder.decompress(block, max_length=MAX_BYTES - size + 1)
                        if decoder
                        else block
                    )
                    size += len(data)
                    if size > MAX_BYTES:
                        raise ValueError("Decoded size limit exceeded")
                    out.write(data)
                if first or (decoder and (not decoder.eof or decoder.unused_data)):
                    raise ValueError("Invalid feed stream")
        feed = PhishTank.from_file(temp)
        if not feed.urls:
            raise ValueError("No usable verified entries")
        digest = hashlib.sha256(temp.read_bytes()).hexdigest()
        temp.replace(FEED)
        print(
            json.dumps(
                {
                    "download": "ok",
                    "usable_urls": len(feed.urls),
                    "bytes": size,
                    "sha256": digest,
                }
            )
        )
        return 0
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def spanish_test_number(value):
    """Validate an explicitly supplied test number without any network access."""
    import phonenumbers

    if not re.fullmatch(r"[+0-9 ()-]{1,40}", value):
        raise ValueError("Invalid phone syntax")
    try:
        number = phonenumbers.parse(value, "ES")
    except phonenumbers.NumberParseException:
        raise ValueError("Invalid Spanish number") from None
    if not phonenumbers.is_valid_number_for_region(number, "ES"):
        raise ValueError("Invalid Spanish number")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


async def probe(name, diagnostic, test_phone=None):
    async with httpx.AsyncClient(
        timeout=5, follow_redirects=False, trust_env=False
    ) as client:
        if name == "phishtank":
            provider = PhishTank.from_file(FEED)
            if not provider.urls:
                raise ValueError("Empty feed")
            indicator = ("url", min(provider.urls))
        elif name == "virustotal":
            key = os.getenv("AVIZOR_VT_KEY")
            if not key:
                raise ValueError("Missing VirusTotal key")
            provider = VirusTotal(client, key)
            indicator = ("domain", "example.com")
        elif name == "numverify":
            if test_phone is None:
                raise ValueError("Explicit phone required")
            key = os.getenv("AVIZOR_NUMVERIFY_KEY")
            if not key:
                raise ValueError("Missing Numverify key")
            provider = Numverify(client, key)
            indicator = ("phone", spanish_test_number(test_phone))
        else:
            key = os.getenv("AVIZOR_GSB_KEY")
            if not key:
                raise ValueError("Missing Google key")
            provider = SafeBrowsing(client, key)
            indicator = ("url", "https://testsafebrowsing.appspot.com/")
        started = time.monotonic()
        if diagnostic:
            signal = await asyncio.wait_for(provider.check(*indicator), timeout=5)
            elapsed = (time.monotonic() - started) * 1000
        else:
            result = await ReputationService([provider], Config()).check(*indicator)
            signal = result.signals[0]
            elapsed = result.elapsed_ms
        print(
            json.dumps(
                {
                    "provider": signal.provider,
                    "status": signal.status,
                    "score": signal.score,
                    "reason": signal.reason,
                    "elapsed_ms": round(elapsed, 2),
                    "mode": "diagnostic_5s" if diagnostic else "fast_350ms",
                    "within_400ms": elapsed < 400,
                }
            )
        )
        return int(
            signal.status == "unavailable"
            or (name == "phishtank" and signal.status != "malicious")
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "provider",
        choices=["download", "phishtank", "virustotal", "google", "numverify"],
    )
    parser.add_argument("--diagnostic", action="store_true")
    parser.add_argument(
        "--authorized-phone",
        action="store_true",
        help="Explicit opt-in to send your own authorized Spanish test number",
    )
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    try:
        if args.provider == "download":
            return download()
        if args.provider == "numverify":
            if not args.authorized_phone:
                raise ValueError("Explicit authorization required")
            if not os.getenv("AVIZOR_NUMVERIFY_KEY"):
                raise ValueError("Missing Numverify key")
            if not sys.stdin.isatty():
                raise ValueError("Interactive terminal required")
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                test_phone = getpass("Own authorized Spanish test number (hidden): ")
            return asyncio.run(probe(args.provider, args.diagnostic, test_phone))
        return asyncio.run(probe(args.provider, args.diagnostic))
    except (
        OSError,
        ValueError,
        TypeError,
        EOFError,
        httpx.HTTPError,
        TimeoutError,
        ImportError,
        GetPassWarning,
    ) as exc:
        # Never print exception text: it may contain credentials or indicators.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
