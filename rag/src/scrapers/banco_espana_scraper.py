"""ES: Fraude financiero de Banco de España. EN: Financial fraud notices."""

from .common import Source

SOURCE = Source(
    name="banco_espana",
    host="clientebancario.bde.es",
    indexes=(
        (
            "https://clientebancario.bde.es/pcb/es/blog/"
            "?blog=%2Fwebcb%2FBlog%2FEducacionFinanciera"
        ),
        (
            "https://clientebancario.bde.es/pcb/es/menu-horizontal/"
            "actualidadeducac/educacion-financiera/fraude-internet.html"
        ),
        (
            "https://clientebancario.bde.es/pcb/es/menu-horizontal/"
            "actualidadeducac/educacion-financiera/protegete-contra-el-fraude/"
        ),
        "https://clientebancario.bde.es/pcb/es/blog/",
    ),
    article_pattern=r"/pcb/es/blog/[A-Za-z0-9_%-]+\.html",
    body_selectors=(
        "[itemprop='articleBody']",
        ".article-body",
        ".blog-content",
        "article",
    ),
    publisher="banco_espana",
)
