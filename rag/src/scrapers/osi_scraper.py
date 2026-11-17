"""ES: Canal ciudadano OSI de INCIBE. EN: INCIBE citizen blog channel."""

from .common import Source

# Separate blog route, not a second copy of the INCIBE alerts listing.
SOURCE = Source(
    name="osi",
    host="www.incibe.es",
    indexes=(
        "https://www.incibe.es/ciudadania/blog",
        "https://www.incibe.es/index.php/ciudadania/blog",
    ),
    article_pattern=r"/(?:index\.php/)?ciudadania/blog/[A-Za-z0-9_%-]+/?",
    body_selectors=(
        "article .field--name-body.field--type-text-with-summary",
        "article .node__content",
        "article",
        ".field--name-body",
    ),
    publisher="incibe",
)
