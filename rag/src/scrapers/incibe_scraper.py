"""ES: Avisos de INCIBE. EN: INCIBE citizen alerts."""

from .common import Source

SOURCE = Source(
    name="incibe",
    host="www.incibe.es",
    indexes=(
        "https://www.incibe.es/ciudadania/avisos",
        "https://www.incibe.es/index.php/ciudadania/avisos",
    ),
    article_pattern=r"/(?:index\.php/)?ciudadania/avisos/[A-Za-z0-9_%-]+/?",
    body_selectors=(
        "article .avisos-wrapper",
        "article .node__content",
        "article",
        ".field--name-body",
    ),
    publisher="incibe",
)
