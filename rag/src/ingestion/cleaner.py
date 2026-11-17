"""Clean input without following links or changing its meaning."""

import hashlib
import unicodedata

from bs4 import BeautifulSoup


def clean_text(text: str, *, is_html: bool = False) -> str:
    """Normalize NFC and whitespace; parse HTML only when explicitly requested."""
    if is_html:
        soup = BeautifulSoup(text, "html.parser")
        for node in soup.select(
            "script, style, nav, footer, header, iframe, form, aside"
        ):
            node.decompose()
        text = soup.get_text(" ", strip=True)
    return " ".join(unicodedata.normalize("NFC", text).split())


def content_hash(text: str) -> str:
    """Match the #40 normalized-text SHA256 convention."""
    return "sha256:" + hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest()
