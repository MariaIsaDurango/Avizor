"""Extracción de texto de adjuntos en el servidor (#164).
Server-side attachment text extraction (#164).

ES: Solo PDF con capa de texto (pypdf, sin dependencias del sistema). El OCR de
    imágenes en el servidor queda pendiente (#7): el móvil puede enviar el
    texto ya extraído y anonimizado (local_preprocessing).
    El binario y el texto sin anonimizar solo viven en memoria durante la
    petición: nunca se guardan ni se registran en logs.
EN: Only PDFs with a text layer (pypdf, no system dependencies). Server OCR
    for images is pending (#7): the phone can send the text already extracted
    and anonymized (local_preprocessing).
    The binary and the raw text only live in memory during the request: they
    are never stored or logged.
"""

import logging
import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

logger = logging.getLogger(__name__)

PDF_ENGINE = "server-pypdf"
# ES: Límites contra PDFs enormes o maliciosos. EN: Limits against huge PDFs.
MAX_PDF_PAGES = 20
MAX_TEXT_CHARS = 5000
PDF_MAGIC = b"%PDF-"


def is_pdf(data: bytes) -> bool:
    """ES: Comprueba la firma real, no solo el mime declarado.
    EN: Checks the real signature, not only the declared mime.
    """
    return data[:1024].lstrip().startswith(PDF_MAGIC)


def extract_pdf_text(data: bytes) -> str:
    """ES: Texto de las primeras páginas, como máximo MAX_TEXT_CHARS. Un PDF
    cifrado, escaneado (sin capa de texto) o dañado devuelve "".
    EN: Text of the first pages, at most MAX_TEXT_CHARS. An encrypted, scanned
    (no text layer) or broken PDF returns "".
    """
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            return ""
        parts: list[str] = []
        size = 0
        for page in reader.pages[:MAX_PDF_PAGES]:
            text = page.extract_text() or ""
            parts.append(text)
            size += len(text)
            if size >= MAX_TEXT_CHARS:
                break
    except (PyPdfError, ValueError, KeyError, TypeError, OSError, RecursionError):
        # ES/EN: fixed message only, never the content
        logger.warning("PDF attachment could not be read")
        return ""
    text = re.sub(r"[ \t]+", " ", "\n".join(parts))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_TEXT_CHARS]
