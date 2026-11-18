"""Concurrent reputation checks with one shared deadline per analysis."""

import asyncio
import time
from dataclasses import replace

from rag.src.reputation import validators
from rag.src.reputation.cache import TTLCache
from rag.src.reputation.config import Config
from rag.src.reputation.models import ReputationResult, Signal
from rag.src.reputation.providers.numverify import Numverify
from rag.src.reputation.providers.safe_browsing import SafeBrowsing
from rag.src.reputation.providers.virustotal import VirusTotal


class ReputationService:
    def __init__(self, providers=(), config=None):
        self.providers = tuple(providers)
        self.config = config or Config()
        self.cache = TTLCache()

    async def _one(self, provider, kind, value):
        key = self.cache.key(provider.name, kind, value)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            result = await provider.check(kind, value)
            if not isinstance(result, Signal):
                raise TypeError("Invalid provider result")
        # Isolate external provider failures to preserve classifier fallback.
        except Exception:  # noqa: BLE001
            return Signal(provider.name, "unavailable", reason="provider_failed")
        # Do not cache stale feed or quota errors; phone numbers are never cached.
        if (
            kind != "phone"
            and provider.name != "phishtank"
            and result.status != "unavailable"
            and result.ttl > 0
        ):
            self.cache.put(key, result, result.ttl)
        return result

    async def check(self, kind, value):
        return await self.check_many([(kind, value)])

    async def check_many(self, indicators):
        started = time.monotonic()
        jobs = {}
        signals = []
        seen = set()
        for index, (kind, value) in enumerate(indicators[:10]):
            try:
                validator = {
                    "url": validators.url,
                    "domain": validators.domain,
                    "phone": validators.phone,
                }[kind]
                value = validator(value)
            except (ValueError, TypeError, KeyError, AttributeError):
                signals.append(
                    Signal(
                        "validator",
                        "invalid",
                        reason="invalid_indicator",
                        indicator_index=index,
                    )
                )
                continue
            if (kind, value) in seen:
                continue
            seen.add((kind, value))
            for provider in self.providers:
                if kind in provider.kinds:
                    job = asyncio.create_task(self._one(provider, kind, value))
                    jobs[job] = (provider.name, index)
        if jobs:
            remaining = max(
                0, self.config.budget_ms / 1000 - (time.monotonic() - started)
            )
            try:
                done, pending = await asyncio.wait(jobs, timeout=remaining)
                for job in jobs:
                    if job in done:
                        signals.append(
                            replace(job.result(), indicator_index=jobs[job][1])
                        )
                    else:
                        signals.append(
                            Signal(
                                jobs[job][0],
                                "unavailable",
                                reason="deadline_exceeded",
                                indicator_index=jobs[job][1],
                            )
                        )
                for job in pending:
                    job.cancel()
            finally:
                for job in jobs:
                    if not job.done():
                        job.cancel()
                await asyncio.gather(*jobs, return_exceptions=True)
        if not signals:
            signals.append(
                Signal("service", "unknown", reason="no_provider_or_indicator")
            )
        return ReputationResult(tuple(signals), (time.monotonic() - started) * 1000)


def build_service(client, config=None, local_providers=()):
    config = config or Config.from_env()
    providers = list(local_providers)
    if config.allow_external_urls:
        if config.virustotal_key:
            providers.append(VirusTotal(client, config.virustotal_key))
        if config.google_key:
            providers.append(SafeBrowsing(client, config.google_key))
    if config.allow_external_phones and config.numverify_key:
        providers.append(Numverify(client, config.numverify_key))
    return ReputationService(providers, config)


async def fast_path(classify, service, indicators):
    """Backend seam: classifier output unchanged; reputation is an extra signal.

    classify is an async callable. Backend owns risk/action policy.
    """
    classification, reputation = await asyncio.gather(
        classify(), service.check_many(indicators)
    )
    return classification, reputation
