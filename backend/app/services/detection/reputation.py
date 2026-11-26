"""Fast-path bridge: local feed by default; reviewed public indicators only abroad."""

import asyncio
import logging
import sys
from contextvars import ContextVar
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

import httpx

# The repo is a monorepo: app.main also runs with backend/ as working directory.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.src.reputation import validators
from rag.src.reputation.config import Config
from rag.src.reputation.models import Signal
from rag.src.reputation.providers.openspam import OpenSpam
from rag.src.reputation.providers.phishtank import PhishTank
from rag.src.reputation.service import ReputationService, build_service

from app.services.detection.decision import (
    apply_phone_reputation,
    apply_url_reputation,
)
from app.services.detection.url_rules import UrlFinding, domain_of

logger = logging.getLogger(__name__)
_private_request = ContextVar("reputation_private_request", default=False)


class _PrivateRequestFilter(logging.Filter):
    def filter(self, record):
        return not _private_request.get()


class _ReviewedProvider:
    """Never send arbitrary user URLs or any phone to a third party."""

    def __init__(self, provider, approved_urls):
        self.provider = provider
        self.name = provider.name
        self.kinds = tuple(k for k in provider.kinds if k in ("url", "domain"))
        self.urls = frozenset(approved_urls)
        self.domains = frozenset(urlsplit(u).hostname for u in self.urls)

    async def check(self, kind, value):
        approved = self.urls if kind == "url" else self.domains
        if kind not in self.kinds or value not in approved:
            return Signal(self.name, "unknown", reason="not_approved_for_egress", ttl=0)
        token = _private_request.set(True)
        try:
            return await self.provider.check(kind, value)
        finally:
            _private_request.reset(token)


def _approved_urls(values):
    approved = set()
    for value in values:
        try:
            parts = urlsplit(value)
            if parts.query or parts.fragment:
                continue
            approved.add(validators.url(value))
        except (ValueError, TypeError, AttributeError):
            continue
    return approved


class ReputationRuntime:
    def __init__(
        self, service, approved_urls=(), phone_provider=None, phone_budget=0.6
    ):
        self.service = service
        self.approved_urls = frozenset(approved_urls)
        # ES: #168 OpenSpam, solo con AVIZOR_EXTERNAL_PHONES=1. EN: opt-in only.
        self.phone_provider = phone_provider
        self.phone_budget = phone_budget

    async def _phone_signal(self, e164):
        # ES: El número va en la URL: nunca a los logs de httpx.
        # EN: The number is in the URL: never in httpx logs.
        token = _private_request.set(True)
        try:
            return await self.phone_provider.check("phone", e164)
        finally:
            _private_request.reset(token)

    async def evaluate_phone(self, classify, e164):
        """ES: Decisión local (reportes, prefijo 400) + OpenSpam en paralelo.
        Si OpenSpam tarda más del presupuesto o falla, vale la decisión local.
        La consulta sigue en segundo plano y llena la caché de 24 h, así una
        respuesta lenta no gasta la cuota dos veces.
        EN: Local decision + OpenSpam in parallel. If OpenSpam is slow or fails,
        the local decision stands. The lookup keeps running in the background
        and fills the 24 h cache, so a slow answer does not spend quota twice.
        """
        if self.phone_provider is None:
            return await asyncio.to_thread(classify)
        lookup = asyncio.create_task(self._phone_signal(e164))

        async def signal():
            try:
                return await asyncio.wait_for(
                    asyncio.shield(lookup), timeout=self.phone_budget
                )
            except Exception:  # noqa: BLE001
                # ES/EN: fixed text only, the number is never logged.
                logger.warning("Phone reputation unavailable; preserving baseline")
                return None

        baseline, result = await asyncio.gather(asyncio.to_thread(classify), signal())
        if result is None or result.status not in ("malicious", "suspicious"):
            return baseline
        if type(result.score) is not int:
            return baseline
        return apply_phone_reputation(baseline, result.status, result.score, "OpenSpam")

    async def evaluate(self, classify, urls, channel):
        """Run pure baseline decision in a worker, network IO on the app loop."""
        # Keep exact URL matches first. A domain is a distinct indicator, never
        # inferred malicious merely because one URL on that host is listed.
        indicators = list(dict.fromkeys(("url", u) for u in urls))[:10]
        for _, raw in tuple(indicators):
            try:
                normalized = validators.url(raw)
            except (ValueError, TypeError, AttributeError):
                continue
            if normalized in self.approved_urls:
                pair = ("domain", urlsplit(normalized).hostname)
                if pair not in indicators and len(indicators) < 10:
                    indicators.append(pair)

        async def reputation():
            try:
                return await self.service.check_many(indicators)
            except Exception:  # noqa: BLE001
                # Do not log exception values: they can contain URL data.
                logger.warning("Reputation unavailable; preserving baseline")
                return None

        baseline, result = await asyncio.gather(
            asyncio.to_thread(classify), reputation()
        )
        if result is None:
            return baseline
        findings = []
        for signal in result.signals:
            index = signal.indicator_index
            if (
                signal.status not in ("malicious", "suspicious")
                or type(signal.score) is not int
                or not 0 <= signal.score <= 100
                or type(index) is not int
                or not 0 <= index < len(indicators)
            ):
                continue
            kind, value = indicators[index]
            try:
                host = (
                    domain_of(validators.url(value))
                    if kind == "url"
                    else validators.domain(value)
                )
            except (ValueError, TypeError, AttributeError):
                continue
            if not host or len(host) > 255:
                continue
            label = {
                "phishtank": "PhishTank",
                "virustotal": "VirusTotal",
                "google_safe_browsing": "Google Safe Browsing",
            }.get(signal.provider)
            if not label:
                continue
            target = "enlace concreto" if kind == "url" else "dominio"
            reason = f"{label} informa de riesgo en el {target}."
            findings.append(UrlFinding(host, signal.score / 100, [reason]))
        return apply_url_reputation(baseline, channel, findings)


def create_runtime(client, settings):
    """Create one runtime per app lifespan: shared cache, quotas and feed."""
    local = []
    if settings.AVIZOR_PHISHTANK_LOCAL:
        path = ROOT / "rag/data/reputation/online-valid.json"
        try:
            local.append(PhishTank.from_file(path))
        except (OSError, ValueError, TypeError):
            logger.warning("PhishTank snapshot missing or invalid; using baseline")
    approved = _approved_urls(settings.AVIZOR_REPUTATION_PUBLIC_URLS)
    config = Config(
        virustotal_key=settings.AVIZOR_VT_KEY.get_secret_value(),
        google_key=settings.AVIZOR_GSB_KEY.get_secret_value(),
        allow_external_urls=settings.AVIZOR_EXTERNAL_URLS and bool(approved),
        # No per-request third-party phone consent in Contract v1.0.0.
        allow_external_phones=False,
    )
    external = build_service(client, config=config).providers
    providers = local + [_ReviewedProvider(p, approved) for p in external]
    # ES: #168 OpenSpam: solo con AVIZOR_EXTERNAL_PHONES=1 y clave.
    # EN: #168 OpenSpam: only with AVIZOR_EXTERNAL_PHONES=1 and a key.
    phone_provider = None
    key = getattr(settings, "AVIZOR_OPENSPAM_KEY", None)
    openspam_key = key.get_secret_value() if key else ""
    if getattr(settings, "AVIZOR_EXTERNAL_PHONES", False) and openspam_key:
        phone_provider = OpenSpam(client, openspam_key)
    return ReputationRuntime(
        ReputationService(providers, config),
        approved,
        phone_provider=phone_provider,
        phone_budget=getattr(settings, "AVIZOR_PHONE_BUDGET_MS", 600) / 1000,
    )


def install_private_request_filters():
    """Suppress request URLs/headers in HTTPX and HTTPcore for our calls only."""
    filter_ = _PrivateRequestFilter()
    names = {
        "httpx",
        "httpcore",
        "httpcore.connection",
        "httpcore.connection_pool",
        "httpcore.http11",
        "httpcore.http2",
        "httpcore.proxy",
        "httpcore.socks_proxy",
    }
    names.update(
        n for n in logging.Logger.manager.loggerDict if n.startswith("httpcore.")
    )
    for name in names:
        logging.getLogger(name).addFilter(filter_)
    return partial(_remove_filters, names, filter_)


def _remove_filters(names, filter_):
    for name in names:
        logging.getLogger(name).removeFilter(filter_)


def new_client():
    return httpx.AsyncClient(
        timeout=httpx.Timeout(0.35),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        follow_redirects=False,
        trust_env=False,
    )
