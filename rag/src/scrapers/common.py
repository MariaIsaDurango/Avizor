"""ES: Infraestructura común de scraping. EN: Shared scraping infrastructure."""

import hashlib
import json
import re
import time
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "AvizorResearch/0.1"
MAX_BYTES = 2_000_000
MAX_REQUESTS = 100
FRAUD = re.compile(
    r"phishing|smishing|vishing|qrishing|whatsapping|fraud|estaf|"
    r"suplant|ciber(?:delinc|ataque|seguridad)|malware|engaño|"
    r"spoofing|ransomware|ingeniería social|clonación de voz|"
    r"robo de identidad|robo de datos|alertas? falsas?|"
    r"mensajes? falsos?|llamadas? falsas?|correos? falsos?|"
    r"enlaces? maliciosos?|enlaces? fraudulentos?|"
    r"venta segura|compras? seguras?|"
    r"antes de hacer click?|autoridades europeas nos advierten",
    re.IGNORECASE,
)
# Police press releases cover many crimes unrelated to digital consumer fraud.
POLICE_DIRECT = re.compile(
    r"phishing|smishing|vishing|qrishing|whatsapping|spoofing|"
    r"ingeniería social|clonación de voz|robo de credenciales|"
    r"malware|ransomware|estafas? informáticas?|fraudes? informáticos?",
    re.IGNORECASE,
)
POLICE_FRAUD = re.compile(r"estaf|fraud|suplant|engaño", re.IGNORECASE)
POLICE_CONTEXT = re.compile(
    r"banc[oa]s?|financier[oa]s?|antifraude|digital|online|internet|"
    r"informátic|telefón|llamadas?|sms|whatsapp|telegram|"
    r"mensajes?|correos?|credenciales|enlaces?|redes sociales|"
    r"tarjetas?|bizum|criptomonedas?|inversiones?",
    re.IGNORECASE,
)
POLICE_EXCLUSIONS = re.compile(
    r"seguridad social|hacienda pública|fraude carrusel|"
    r"documentación fraudulent|uso fraudulento de documentación|"
    r"blanqueo|parameter tampering",
    re.IGNORECASE,
)


MONTHS = dict(
    zip(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ],
        range(1, 13),
        strict=True,
    )
)


def relevant_title(title: str, source_name: str) -> bool:
    """ES: Relevancia por fuente. EN: Source-specific title relevance."""
    if source_name != "policia_nacional":
        return bool(FRAUD.search(title))
    if POLICE_EXCLUSIONS.search(title):
        return False
    return bool(
        POLICE_DIRECT.search(title)
        or (POLICE_FRAUD.search(title) and POLICE_CONTEXT.search(title))
    )


@dataclass(frozen=True)
class Source:
    """ES: Configuración de un canal. EN: Source configuration."""

    name: str
    host: str
    indexes: tuple[str, ...]
    article_pattern: str
    body_selectors: tuple[str, ...]
    relevant_only: bool = True
    publisher: str = ""

    def article_url(self, url: str, base: str = "") -> str | None:
        """Return canonical official article URL, never an arbitrary link."""
        try:
            parts = urlsplit(urljoin(base, url))
            if not valid_origin(parts, self.host):
                return None
            if re.search(r"(?i)%(?:2f|5c|2e|25)", parts.path):
                return None
            if not re.fullmatch(self.article_pattern, parts.path):
                return None
            if self.name == "banco_espana" and re.fullmatch(
                r"/pcb/es/blog/index\d*\.html", parts.path
            ):
                return None
            query = ""
            if self.name == "policia_nacional":
                ids = [v for k, v in parse_qsl(parts.query) if k == "ID"]
                if len(ids) != 1 or not re.fullmatch(r"[0-9]{1,10}", ids[0]):
                    return None
                query = urlencode({"ID": ids[0]})
            return urlunsplit(("https", self.host, parts.path, query, ""))
        except ValueError:
            return None

    def index_url(self, url: str, base: str = "") -> str | None:
        """Accept only configured listing paths and bounded pagination."""
        try:
            parts = urlsplit(urljoin(base, url))
            if not valid_origin(parts, self.host):
                return None
            allowed_path = parts.path in {urlsplit(u).path for u in self.indexes}
            if self.name == "banco_espana":
                allowed_path = allowed_path or bool(
                    re.fullmatch(r"/pcb/es/blog/index[0-9]{1,3}\.html", parts.path)
                )
            if not allowed_path:
                return None
            params = parse_qsl(parts.query)
            if self.name == "banco_espana" and params in (
                [("blog", "/webcb/Blog")],
                [("blog", "/webcb/Blog/EducacionFinanciera")],
            ):
                return urlunsplit(
                    ("https", self.host, parts.path, urlencode(params), "")
                )
            if len(params) > 1 or any(
                k not in {"page", "pagina"} or not v.isdigit() or int(v) > 100
                for k, v in params
            ):
                return None
            return urlunsplit(("https", self.host, parts.path, urlencode(params), ""))
        except ValueError:
            return None


def valid_origin(parts, host: str) -> bool:
    """Exact HTTPS origin; no credentials or alternative ports."""
    return (
        parts.scheme == "https"
        and parts.netloc.lower() == host
        and parts.username is None
        and parts.password is None
    )


def normalize(text: str) -> str:
    """Normalize only Unicode and whitespace, preserving meaning."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Notice:
    """Raw notice; metadata-only records are not eligible for indexing."""

    source: str
    publisher: str
    url: str
    title: str
    published_at: str
    scraped_at: str
    language: str
    text: str | None
    content_hash: str | None
    metadata_hash: str
    reuse_reference: str | None

    def to_dict(self) -> dict:
        return asdict(self)


class FetchError(RuntimeError):
    """An access or parsing problem, not a reason to bypass restrictions."""


def robots_normalize(value: str) -> str:
    """Normalize percent-encoding for robots comparisons (RFC 9309)."""

    def replace(match: re.Match) -> str:
        char = chr(int(match[0][1:], 16))
        return (
            char
            if char.isascii() and (char.isalnum() or char in "-._~")
            else match[0].upper()
        )

    value = re.sub(r"%[0-9a-fA-F]{2}", replace, value)
    return quote(value, safe="/%!$&'()*+,;=:@?[]~-._")


class RobotsPolicy:
    """Read applicable groups and honor wildcards, anchors and longest matches."""

    def __init__(self, content: str):
        groups: list[tuple[list[str], list[tuple[str, str]]]] = []
        agents: list[str] = []
        rules: list[tuple[str, str]] = []
        for line in content.lstrip("\ufeff").splitlines():
            line = line.split("#", 1)[0].strip()
            key, separator, value = line.partition(":")
            if not separator:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent" and value:
                if rules:
                    groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
            elif agents and key in {"allow", "disallow", "crawl-delay", "request-rate"}:
                rules.append((key, value))
        if agents:
            groups.append((agents, rules))
        if (
            content.strip()
            and not groups
            and not all(
                not line.split("#", 1)[0].strip()
                or line.lower().strip().startswith("sitemap:")
                for line in content.splitlines()
            )
        ):
            raise FetchError("Unrecognized robots.txt")
        token = USER_AGENT.split("/", 1)[0].lower()
        scores = [
            max(
                (len(a) if a != "*" else 0 for a in agents if a == "*" or a in token),
                default=-1,
            )
            for agents, _ in groups
        ]
        best = max(scores, default=-1)
        self.rules = [
            rule
            for score, (_, group_rules) in zip(scores, groups, strict=True)
            if score == best and score >= 0
            for rule in group_rules
        ]
        self.delay = 0.0
        for key, value in self.rules:
            try:
                if key == "crawl-delay":
                    self.delay = max(self.delay, float(value))
                elif key == "request-rate":
                    requests, seconds = map(float, value.split("/"))
                    if requests > 0:
                        self.delay = max(self.delay, seconds / requests)
            except ValueError:
                continue

    def can_fetch(self, url: str) -> bool:
        parts = urlsplit(url)
        target = robots_normalize(
            parts.path + ("?" + parts.query if parts.query else "")
        )
        matched = []
        for key, value in self.rules:
            if key not in {"allow", "disallow"} or not value:
                continue
            pattern = robots_normalize(value)
            anchored = pattern.endswith("$")
            if anchored:
                pattern = pattern[:-1]
            regex = re.escape(pattern).replace(r"\*", ".*") + ("$" if anchored else "")
            if re.match(regex, target):
                matched.append((len(pattern.replace("*", "")), key == "allow"))
        return max(matched, default=(0, True))[1]


POLICE_HOST = "www.policia.es"
POLICE_COOKIES_PAGE = "https://www.policia.es/_es/cookies.php"
POLICE_COOKIES_ENDPOINT = "https://www.policia.es/cookies_set.php"
POLICE_NEWS_ENDPOINT = "https://www.policia.es/js/ajax_cargar_noticias.php"


class SafeFetcher:
    """Sequential, bounded HTML fetcher with per-host robots cache."""

    def __init__(
        self,
        client: httpx.Client,
        delay: float = 2.0,
        budget: int = MAX_REQUESTS,
        accept_police_cookies: bool = False,
    ):
        self.client = client
        self.delay = delay
        self.budget = budget
        self.requests = 0
        self.robots: dict[str, RobotsPolicy] = {}
        self.blocked_hosts: set[str] = set()
        self.last_request: dict[str, float] = {}
        self.accept_police_cookies = accept_police_cookies
        self.police_cookies_ready = False

    def _request(
        self,
        url: str,
        host: str,
        robots: bool = False,
        *,
        method: str = "GET",
        form: dict[str, str] | None = None,
    ) -> str:
        if method != "GET" and not (
            method == "POST"
            and host == POLICE_HOST
            and self.accept_police_cookies
            and (
                (url == POLICE_COOKIES_ENDPOINT and form is None)
                or (
                    url == POLICE_NEWS_ENDPOINT
                    and self.police_cookies_ready
                    and form is not None
                )
            )
        ):
            raise FetchError("Unapproved HTTP method")
        if not valid_origin(urlsplit(url), host):
            raise FetchError("Unapproved origin")
        if host in self.blocked_hosts:
            raise FetchError("Host paused after access failure")
        if self.requests >= self.budget:
            raise FetchError("Request budget exhausted")
        remaining = self.delay - (time.monotonic() - self.last_request.get(host, -1e9))
        if remaining > 0:
            time.sleep(remaining)
        self.requests += 1
        self.last_request[host] = time.monotonic()
        try:
            with self.client.stream(
                method,
                url,
                headers={"User-Agent": USER_AGENT},
                data=form,
                follow_redirects=False,
            ) as response:
                if robots and response.status_code == 404:
                    return "User-agent: *\nDisallow:"
                if response.status_code != 200:
                    if (
                        response.status_code in {401, 403, 429}
                        or response.status_code >= 500
                    ):
                        self.blocked_hosts.add(host)
                    raise FetchError(f"HTTP {response.status_code}; stopped")
                mime = response.headers.get("content-type", "").lower()
                if not robots and method == "GET" and "text/html" not in mime:
                    raise FetchError("Expected HTML")
                if robots and "text/html" in mime:
                    raise FetchError("Unexpected HTML instead of robots.txt")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise FetchError("Response exceeds size limit")
                return data.decode(response.encoding or "utf-8", errors="replace")
        except httpx.HTTPError as exc:
            self.blocked_hosts.add(host)
            raise FetchError(f"Network error: {type(exc).__name__}") from exc

    def _prepare_police_session(self) -> None:
        """ES: Cookies técnicas. EN: Technical cookie session."""
        if self.police_cookies_ready:
            return

        policy = self.robots[POLICE_HOST]
        for url in (POLICE_COOKIES_PAGE, POLICE_COOKIES_ENDPOINT):
            if not policy.can_fetch(url):
                raise FetchError("robots.txt disallows cookie endpoint")

        self._request(POLICE_COOKIES_PAGE, POLICE_HOST)
        result = self._request(
            POLICE_COOKIES_ENDPOINT,
            POLICE_HOST,
            method="POST",
        )
        if result.strip() != "1":
            raise FetchError("Police cookie acceptance not confirmed")
        self.police_cookies_ready = True

    def police_news(self, year: int, month: int, start: str, end: str) -> dict:
        """Fetch one public press batch using the portal's form protocol."""
        if not self.accept_police_cookies or not self.police_cookies_ready:
            raise FetchError("Police cookie session required")
        if not self.robots[POLICE_HOST].can_fetch(POLICE_NEWS_ENDPOINT):
            raise FetchError("robots.txt disallows police news endpoint")
        if not 2000 <= year <= 2100 or not 0 <= month <= 12:
            raise FetchError("Invalid police date filter")
        if any(len(value) > 128 for value in (start, end)):
            raise FetchError("Invalid police pagination cursor")
        raw = self._request(
            POLICE_NEWS_ENDPOINT,
            POLICE_HOST,
            method="POST",
            form={
                "cargar_mas": "si",
                "desde": start,
                "hasta": end,
                "anyo": str(year),
                "mes": str(month),
                "lang": "es",
            },
        )
        try:
            result = json.loads(raw)
        except ValueError as exc:
            raise FetchError("Invalid police news JSON") from exc
        if not isinstance(result, dict) or not isinstance(result.get("contenido"), str):
            raise FetchError("Invalid police news response")
        return result

    def get(self, url: str, source: Source) -> str:
        if source.host in self.blocked_hosts:
            raise FetchError("Host paused after access failure")
        if url not in {source.article_url(url), source.index_url(url)}:
            raise FetchError("Unapproved page")
        if source.host not in self.robots:
            content = self._request(
                f"https://{source.host}/robots.txt", source.host, robots=True
            )
            if "<html" in content.lower():
                raise FetchError("Invalid robots.txt")
            try:
                self.robots[source.host] = RobotsPolicy(content)
            except FetchError:
                self.blocked_hosts.add(source.host)
                raise
        parser = self.robots[source.host]
        if not parser.can_fetch(url):
            raise FetchError("robots.txt disallows access")
        # Avoid hanging on a very long server-requested delay. Resume only manually.
        if parser.delay > 60:
            self.blocked_hosts.add(source.host)
            raise FetchError("robots.txt requests a long delay; reschedule manually")
        self.delay = max(self.delay, parser.delay)
        if (
            source.name == "policia_nacional"
            and source.host == POLICE_HOST
            and self.accept_police_cookies
        ):
            self._prepare_police_session()

        html = self._request(url, source.host)
        soup = BeautifulSoup(html, "html.parser")
        title = normalize(soup.title.get_text(" ", strip=True)) if soup.title else ""
        if re.search(
            r"captcha|access denied|just a moment|acceso denegado", title, re.IGNORECASE
        ):
            self.blocked_hosts.add(source.host)
            raise FetchError("Access challenge; stopped")
        return html


def parse_date(value: str) -> date | None:
    """Parse ISO and common Spanish publication dates (no guessed dates)."""
    value = normalize(value)
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})(?!\d)", value)
    try:
        if match:
            return date(*map(int, match.groups()))
        match = re.search(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4}|\d{2})\b", value)
        if match:
            day, month, year = map(int, match.groups())
            return date(year + 2000 if year < 100 else year, month, day)
        match = re.search(r"\b(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\b", value.lower())
        if match and match[2] in MONTHS:
            return date(int(match[3]), MONTHS[match[2]], int(match[1]))
    except ValueError:
        return None
    return None


def publication_date(soup: BeautifulSoup, heading) -> date | None:
    """Prefer publication metadata or date immediately near title."""
    candidates = []
    for tag in soup.select(
        'meta[property="article:published_time"], meta[itemprop="datePublished"], '
        '[itemprop="datePublished"], article time[datetime], main time[datetime], '
        "article .date-published, main .date-published, article .fecha-publicacion, "
        "main .fecha-publicacion, article .fecha, main .fecha"
    ):
        candidates.append(
            tag.get("content") or tag.get("datetime") or tag.get_text(" ", strip=True)
        )
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            obj = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        items = (
            obj
            if isinstance(obj, list)
            else obj.get("@graph", [obj])
            if isinstance(obj, dict)
            else []
        )
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("datePublished"), str):
                candidates.insert(0, item["datePublished"])
    # BDE articles can show the date as plain text just after the heading.
    for tag in heading.find_all_next(["p", "span", "div", "time"], limit=18):
        value = normalize(tag.get_text(" ", strip=True))
        if len(value) <= 55 and re.fullmatch(
            r"(?i)(?:(?:fecha(?: de publicación)?|publicado(?: el)?)\s*:?\s*)?"
            r"(?:\d{1,2}[/.-]\d{1,2}[/.-](?:\d{4}|\d{2})|\d{4}-\d{2}-\d{2}|"
            r"\d{1,2} de \w+ de \d{4})",
            value,
        ):
            candidates.append(value)
    return next(
        (parsed for item in candidates if (parsed := parse_date(str(item)))), None
    )


def cutoff_date(today: date, months: int = 24) -> date:
    """Calendar-month cutoff, handling leap days."""
    n = today.year * 12 + today.month - 1 - months
    year, month = divmod(n, 12)
    day = today.day
    while day > 0:
        try:
            return date(year, month + 1, day)
        except ValueError:
            day -= 1
    raise ValueError("Invalid cutoff")


def parse_notice(
    html: str,
    url: str,
    source: Source,
    today: date,
    reuse_reference: str | None = None,
) -> Notice | None:
    """Extract a recent notice; only extract body after explicit reuse review."""
    if source.article_url(url) != url:
        raise ValueError("Noncanonical article URL")
    soup = BeautifulSoup(html, "html.parser")
    selectors = ("article h1", "article h2", "main h1", "main h2", "h1")
    if source.name == "policia_nacional":
        selectors = (
            ".contenidoNoticia h2",
            ".noticia h2",
            "article h2",
            "article h1",
            "main h2",
            "h2",
            "main h1",
            "h1",
        )
    heading = next(
        (h for selector in selectors if (h := soup.select_one(selector))), None
    )
    if not heading:
        return None
    title = normalize(heading.get_text(" ", strip=True))
    published = publication_date(soup, heading)
    if not title or not published or not cutoff_date(today) <= published <= today:
        return None
    if source.relevant_only and not relevant_title(title, source.name):
        return None
    text = None
    if reuse_reference:
        body = next(
            (
                node
                for selector in source.body_selectors
                if (node := soup.select_one(selector))
            ),
            None,
        )
        if body is None:
            return None
        for node in body.select(
            "script, style, nav, header, footer, form, aside, iframe, button, figure"
        ):
            node.decompose()
        # Text only; never extract link targets or download embedded files.
        text = normalize(body.get_text(" ", strip=True))
        if len(text) < 80:
            return None
    return Notice(
        source=source.name,
        publisher=source.publisher or source.name,
        url=url,
        title=title,
        published_at=published.isoformat(),
        scraped_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        language="es",
        text=text,
        content_hash=sha256_text(text) if text else None,
        metadata_hash=sha256_text(f"{title}\n{published.isoformat()}"),
        reuse_reference=reuse_reference,
    )


def is_bank_education_index(url: str) -> bool:
    """Return whether the URL is the official financial education blog index."""
    parts = urlsplit(url)
    return (
        valid_origin(parts, "clientebancario.bde.es")
        and bool(re.fullmatch(r"/pcb/es/blog/(?:index[0-9]{1,3}\.html)?", parts.path))
        and parse_qsl(parts.query) == [("blog", "/webcb/Blog/EducacionFinanciera")]
    )


def bank_page_number(url: str) -> int:
    """Return the advertised page number; the category root is page one."""
    match = re.search(r"/index([0-9]{1,3})\.html$", urlsplit(url).path)
    return int(match.group(1)) if match else 1


def discover(html: str, index: str, source: Source) -> tuple[list[str], list[str]]:
    """Find only whitelisted official articles and pagination links."""
    soup = BeautifulSoup(html, "html.parser")
    links, pages = [], []
    for anchor in soup.select("a[href]"):
        href = str(anchor["href"])
        article = source.article_url(href, index)
        if article:
            # Police listing is broad; keep plausible fraud titles, plus empty anchors
            # (actual relevance is checked again from the article title).
            label = normalize(anchor.get_text(" ", strip=True))
            if (
                source.name in {"policia_nacional", "osi", "banco_espana"}
                and label
                and not FRAUD.search(label)
                and not re.search(
                    r"leer|más información|ampliar|ver noticia", label, re.IGNORECASE
                )
            ):
                continue
            links.append(article)
        page = source.index_url(href, index)
        if page and page != index:
            pages.append(page)
    if source.name == "banco_espana" and is_bank_education_index(index):
        current = bank_page_number(index)
        pages = [
            page
            for page in pages
            if is_bank_education_index(page) and bank_page_number(page) == current + 1
        ]
    return list(dict.fromkeys(links)), list(dict.fromkeys(pages))


def deduplicate(notices: list[Notice]) -> list[Notice]:
    """Keep newest observations per URL; collapse exact content duplicates."""
    by_url = {}
    for notice in notices:
        key_url = notice.url.replace(
            "https://www.incibe.es/index.php/", "https://www.incibe.es/"
        ).rstrip("/")
        previous = by_url.get(key_url)
        if previous is None or notice.scraped_at >= previous.scraped_at:
            by_url[key_url] = notice
    seen = set()
    unique = []
    for notice in sorted(
        by_url.values(), key=lambda x: (x.published_at, x.url), reverse=True
    ):
        # Metadata-only hashes cannot establish body equivalence.
        key = notice.content_hash or (notice.publisher, notice.metadata_hash)
        if key not in seen:
            unique.append(notice)
            seen.add(key)
    return unique
