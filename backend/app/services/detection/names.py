"""Nombres de personas en el texto que extrae el servidor (#193).
Person names in server-extracted text (#193).

ES: anonymize() (regex-v0, igual que el móvil) no tapa nombres. Para el texto
    de PDF e imágenes, que no pasó por el móvil, se añade un NER de spaCy que
    cambia solo las personas (PER) por [NAME]. Lugares y organizaciones se
    quedan: el nombre del banco o de "Correos" es una señal de la estafa.
    El modelo se carga la primera vez que hace falta (no gasta RAM si nadie
    envía archivos). AVIZOR_NER_MODEL elige el modelo; vacío lo desactiva.
EN: anonymize() (regex-v0, same as the phone) does not mask names. For PDF and
    image text, which never went through the phone, a spaCy NER replaces only
    persons (PER) with [NAME]. Places and organisations stay: the bank's or
    "Correos" name is a scam signal.
    The model loads the first time it is needed (no RAM used if nobody sends
    files). AVIZOR_NER_MODEL picks the model; empty disables it.
"""

import logging
import re
import threading
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

NAME = "[NAME]"
# ES: Solo hace falta el NER. EN: Only the NER is needed.
SPACY_EXCLUDE = ["parser", "lemmatizer", "morphologizer", "attribute_ruler", "senter"]
# ES: Saludos y tratamientos: se quedan, se tapa lo que viene después.
# EN: Greetings and titles stay; what follows is masked.
KEEP_WORDS = {
    "hola", "estimado", "estimada", "querido", "querida", "buenos", "buenas",
    "dias", "días", "tardes", "noches", "sr", "sra", "srta", "don", "doña",
    "dr", "dra", "señor", "señora", "titular", "paciente", "cliente", "nombre",
}  # fmt: skip
# ES: Palabra con forma de nombre: "Carmen", "CARMEN", "María-José".
# EN: Name-shaped word: "Carmen", "CARMEN", "María-José".
NAME_WORD = re.compile(r"^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]*$")
# ES: Partículas entre nombres ("de la Fuente"). EN: Particles inside names.
PARTICLES = {"de", "del", "la", "las", "los", "y"}
ACRONYMS = {"DNI", "NIE", "NIF", "CIF", "IBAN"}
# ES: Familia: en "Mamá, soy yo" es la señal de la estafa, no un nombre.
# EN: Family words: in "Mamá, soy yo" they are the scam signal, not a name.
FAMILY = {
    "mamá",
    "mama",
    "papá",
    "papa",
    "abuela",
    "abuelo",
    "hijo",
    "hija",
    "tía",
    "tío",
}
# ES: Segunda capa sin modelo: tras un tratamiento o etiqueta va un nombre, aunque
#     el NER no lo vea (p. ej. en mayúsculas: "Sr. PEDRO GOMEZ").
# EN: Second, model-free layer: a title or label is followed by a name even
#     when the NER misses it (e.g. upper case: "Sr. PEDRO GOMEZ").
_WORD = r"[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+"
TITLED_NAME = re.compile(
    r"\b(?:Sra?|Srta|Dra?|Don|Doña|Estimad[oa]|Querid[oa]|Titular|Paciente|Nombre)"
    r"\.?:?[ \t]+"
    rf"({_WORD}(?:[ \t]+(?:(?:de|del|la|las|los|y)[ \t]+)*{_WORD}){{0,3}})"
)

_lock = threading.Lock()
_nlp: Any = None
_loaded_name: str | None = None


def _model() -> Any:
    """ES: Carga perezosa y una sola vez; None si está desactivado o falta.
    EN: Lazy, one-time load; None when disabled or missing.
    """
    global _nlp, _loaded_name
    name = settings.AVIZOR_NER_MODEL.strip()
    if not name:
        return None
    if _loaded_name == name:
        return _nlp
    with _lock:
        if _loaded_name != name:
            try:
                import spacy

                _nlp = spacy.load(name, exclude=SPACY_EXCLUDE)
                logger.info("NER model loaded: %s", name)
            except (ImportError, OSError):
                _nlp = None
                logger.warning("NER model %s not available: names are not masked", name)
            _loaded_name = name
    return _nlp


def _is_name_word(word: str) -> bool:
    return (
        bool(NAME_WORD.match(word))
        and word.lower().strip(".") not in KEEP_WORDS
        and word.upper() not in ACRONYMS
    )


def _name_follows(tokens: list[Any], i: int) -> bool:
    """ES: Tras las partículas ("de la") sigue un nombre. EN: A name follows."""
    while i < len(tokens) and tokens[i].text.lower() in PARTICLES:
        i += 1
    return i < len(tokens) and _is_name_word(tokens[i].text)


def _name_runs(tokens: list[Any]) -> list[tuple[int, int]]:
    """ES: Tramos (inicio, fin) de palabras con forma de nombre dentro de una
    entidad PER, sin saludos, tratamientos, siglas ni marcadores [IBAN].
    EN: (start, end) runs of name-shaped words inside a PER entity, without
    greetings, titles, acronyms or [IBAN] markers.
    """
    runs: list[tuple[int, int]] = []
    start = end = None
    for i, token in enumerate(tokens):
        word = token.text
        if _is_name_word(word):
            if start is None:
                start = token.idx
            end = token.idx + len(word)
        elif (
            start is not None
            and word.lower() in PARTICLES
            and _name_follows(tokens, i + 1)
        ):
            continue
        elif start is not None:
            runs.append((start, end))
            start = None
    if start is not None:
        runs.append((start, end))
    return runs


def _titled_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for match in TITLED_NAME.finditer(text):
        words = match.group(1).split()
        if words[0].lower() in FAMILY or words[0].upper() in ACRONYMS:
            continue
        # ES: Quita siglas del final ("Ruiz DNI"). EN: Drop trailing acronyms.
        while words and words[-1].upper() in ACRONYMS:
            words.pop()
        if words:
            start = match.start(1)
            spans.append((start, start + len(" ".join(words))))
    return spans


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def mask_names(text: str) -> str:
    """ES: Cambia los nombres de personas por [NAME]. Sin modelo solo se aplica
    la regla de tratamientos (Sr., Doña, Titular:...).
    EN: Replaces person names with [NAME]. Without a model only the title rule
    (Sr., Doña, Titular:...) applies.
    """
    if not text:
        return text
    spans = _titled_spans(text)
    nlp = _model()
    if nlp is not None:
        for ent in nlp(text).ents:
            if ent.label_ == "PER":
                spans.extend(_name_runs(list(ent)))
    for start, end in reversed(_merge(spans)):
        text = text[:start] + NAME + text[end:]
    return text
