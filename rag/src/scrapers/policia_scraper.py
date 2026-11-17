"""ES: Notas de prensa policiales. EN: Official police press releases."""

from collections.abc import Iterator
from datetime import date

from .common import FetchError, SafeFetcher, Source, cutoff_date, discover

SOURCE = Source(
    name="policia_nacional",
    host="www.policia.es",
    indexes=("https://www.policia.es/_es/comunicacion_salaprensa.php",),
    article_pattern=r"/_es/comunicacion_prensa_detalle\.php",
    body_selectors=(".contenidoNoticia", ".noticia", "article", "main"),
    publisher="policia_nacional",
)


def news_batches(
    source: Source,
    fetcher: SafeFetcher,
    today: date,
    max_pages: int,
    *,
    start_month: date | None = None,
    end_month: date | None = None,
) -> Iterator[tuple[str, list[str]]]:
    """Read recent monthly press batches, honoring the server's cursor."""
    oldest = cutoff_date(today).replace(day=1)
    newest = today.replace(day=1)
    start_month = (start_month or newest).replace(day=1)
    end_month = (end_month or oldest).replace(day=1)
    if not oldest <= end_month <= start_month <= newest:
        raise ValueError("Police month range outside the last 24 months")
    index = source.indexes[0]
    fetcher.get(index, source)
    year, month = start_month.year, start_month.month
    pages = 0
    while (year, month) >= (end_month.year, end_month.month) and pages < max_pages:
        start, end = "", ""
        seen: set[tuple[str, str]] = set()
        while pages < max_pages:
            cursor = (start, end)
            if cursor in seen:
                raise FetchError("Repeated police pagination cursor")
            seen.add(cursor)
            result = fetcher.police_news(year, month, start, end)
            pages += 1
            articles, _ = discover(result["contenido"], index, source)
            yield f"{year}-{month:02d}:{pages}", articles
            if str(result.get("contador")) == "0":
                break
            values = (result.get("desde"), result.get("hasta"))
            if any(type(value) not in (str, int) for value in values):
                raise FetchError("Missing police pagination cursor")
            start, end = map(str, values)
            if not result["contenido"].strip():
                raise FetchError("Empty police news page without end marker")
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
