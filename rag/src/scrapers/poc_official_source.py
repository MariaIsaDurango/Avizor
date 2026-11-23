"""ES: PoC de extracción de metadatos oficiales. EN: Official metadata PoC."""

import json
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

URL = "https://clientebancario.bde.es/pcb/es/blog/advertencias-del-banco-de-espana.html"
USER_AGENT = "AvizorResearch/0.1"


def parse_notice(html: str) -> dict[str, str]:
    """ES: Extrae título y URL fija. EN: Extract title and fixed URL."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("main h1, article h1, h1")
    if title is None or not title.get_text(" ", strip=True):
        raise ValueError("Missing notice title")
    return {
        "source": "banco_espana",
        "url": URL,
        "title": title.get_text(" ", strip=True),
    }


def fetch_notice(client: httpx.Client) -> dict[str, str]:
    """ES: Respeta robots y no sigue redirecciones. EN: Respect robots, no redirects."""
    parts = urlsplit(URL)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    response = client.get(robots_url)
    if response.status_code == 200:
        robots = RobotFileParser()
        robots.parse(response.text.splitlines())
        if not robots.can_fetch(USER_AGENT, URL):
            raise PermissionError("robots.txt disallows access")
    elif response.status_code != 404:
        raise RuntimeError(f"Cannot verify robots.txt: HTTP {response.status_code}")
    response = client.get(URL)
    response.raise_for_status()
    if "text/html" not in response.headers.get("content-type", "").lower():
        raise ValueError("Expected HTML")
    return parse_notice(response.text)


def main() -> None:
    """Run one metadata-only request after checking robots.txt."""
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=15, follow_redirects=False
    ) as client:
        print(json.dumps(fetch_notice(client), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
