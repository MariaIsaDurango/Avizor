"""Extracción de texto de adjuntos en el servidor (#164, #192).
Server-side attachment text extraction (#164, #192).

ES: PDF con capa de texto (pypdf) e imágenes con OCR local (Tesseract, #192).
    Nada sale a terceros. El binario y el texto sin anonimizar solo viven en
    memoria durante la petición: nunca se guardan en disco ni en logs. Por eso
    Tesseract se llama por stdin/stdout y no con pytesseract, que escribe la
    imagen y el resultado en archivos temporales.
EN: PDFs with a text layer (pypdf) and images with local OCR (Tesseract, #192).
    Nothing goes to third parties. The binary and the raw text only live in
    memory during the request: never written to disk or logs. That is why
    Tesseract runs through stdin/stdout and not pytesseract, which writes the
    image and the result to temporary files.
"""

import logging
import os
import re
import shutil
import subprocess
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

logger = logging.getLogger(__name__)

PDF_ENGINE = "server-pypdf"
IMAGE_ENGINE = "server-tesseract"
# ES: Límites contra PDFs enormes o maliciosos. EN: Limits against huge PDFs.
MAX_PDF_PAGES = 20
MAX_TEXT_CHARS = 5000
PDF_MAGIC = b"%PDF-"
# ES: Idioma de Tesseract (paquete tesseract-ocr-spa). EN: Tesseract language.
OCR_LANGUAGE = "spa"
# ES: Tope de tiempo por imagen: el agente tiene 15 s en total.
# EN: Time cap per image: the agent has 15 s in total.
OCR_TIMEOUT_S = 8


def is_pdf(data: bytes) -> bool:
    """ES: Comprueba la firma real, no solo el mime declarado.
    EN: Checks the real signature, not only the declared mime.
    """
    return data[:1024].lstrip().startswith(PDF_MAGIC)


def is_image(data: bytes) -> bool:
    """ES: Firma real de JPEG, PNG, WebP o HEIC (los mime del contrato).
    EN: Real JPEG, PNG, WebP or HEIC signature (the contract mimes).
    """
    return (
        data.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n"))
        or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        or data[4:8] == b"ftyp"
    )


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:MAX_TEXT_CHARS]


def extract_image_text(data: bytes) -> str:
    """ES: Texto visible de la imagen, como máximo MAX_TEXT_CHARS. Si Tesseract
    no está, tarda demasiado o no puede leer el formato (p. ej. HEIC), devuelve "".
    EN: Visible text of the image, at most MAX_TEXT_CHARS. Returns "" when
    Tesseract is missing, too slow or cannot read the format (e.g. HEIC).
    """
    binary = shutil.which("tesseract")
    if binary is None:
        logger.warning("Tesseract is not installed: image OCR skipped")
        return ""
    try:
        # ES: Binario y argumentos fijos. EN: Fixed binary and arguments.
        result = subprocess.run(
            [binary, "stdin", "stdout", "-l", OCR_LANGUAGE],
            input=data,
            capture_output=True,
            timeout=OCR_TIMEOUT_S,
            check=False,
            # ES: Un hilo: varias peticiones a la vez no saturan la CPU.
            # EN: One thread: concurrent requests do not saturate the CPU.
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except subprocess.TimeoutExpired:
        logger.warning("Image OCR timed out")
        return ""
    except OSError:
        logger.warning("Image OCR could not start")
        return ""
    if result.returncode != 0:
        # ES/EN: fixed message only, never stderr or the content
        logger.warning("Image attachment could not be read")
        return ""
    return _clean(result.stdout.decode("utf-8", errors="replace"))


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
    return _clean("\n".join(parts))
