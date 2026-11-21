"""Propuesta automática para revisar el "spam" de SpamSpa (#36).
Automatic proposal to review SpamSpa "spam" (#36).

ES: SpamSpa marca como "spam" tanto la publicidad como las estafas. Este
    script propone una etiqueta para cada uno (spam = publicidad, fraud =
    estafa) y genera un CSV para revisarlo a mano. La propuesta es solo una
    ayuda: la etiqueta buena es la que decide la persona que revisa.
    Uso:  python -m src.classifier.review <train.csv> <salida.csv>
EN: SpamSpa marks both ads and scams as "spam". This script proposes a label
    for each (spam = ad, fraud = scam) and writes a CSV for manual review.
    The proposal is only a hint: the reviewer's label is the one that counts.
"""

import re
import sys
from pathlib import Path

import pandas as pd

from src.classifier.anonymize import anonymize

# ES: Señales típicas de estafa: bancos, premios, paquetes, organismos, urgencia.
# EN: Typical scam signals: banks, prizes, parcels, public bodies, urgency.
FRAUD_SIGNALS = [
    r"\bbanco\b|\bcuenta\b|tarjeta|\bpin\b|contrase|clave|bizum",
    r"bloquead|suspendid|desactivad|verific|confirm|actualiz",
    r"premio|ganad|ganador|sorteo|seleccionad|regalo|herencia",
    r"paquete|envio|envío|entrega|aduana|correos|seur|dhl|mrw",
    r"hacienda|multa|dgt|seguridad social|policia|policía|juzgado",
    r"urgente|inmediat|ultimo aviso|último aviso|caduca|24 ?h",
]
# ES: Señales típicas de publicidad. EN: Typical advertising signals.
AD_SIGNALS = [
    r"oferta|descuento|promoci|rebaja|\d+ ?%|precio|tienda|compra",
    r"suscri|baja\b|stop\b|newsletter|catalogo|catálogo|cupon|cupón",
    r"tarifa|gigas|\bgb\b|minutos|fibra|movil|móvil",
]


def _score(text: str, signals: list[str]) -> int:
    lower = text.lower()
    return sum(bool(re.search(pattern, lower)) for pattern in signals)


def propose(text: str) -> tuple[str, str]:
    """ES: Devuelve (etiqueta propuesta, motivo). EN: Returns (label, reason)."""
    fraud, ads = _score(text, FRAUD_SIGNALS), _score(text, AD_SIGNALS)
    if fraud > ads:
        return "fraud", f"señales de estafa: {fraud}, de publicidad: {ads}"
    return "spam", f"señales de estafa: {fraud}, de publicidad: {ads}"


def build_review(spamspa_path: Path) -> pd.DataFrame:
    raw = pd.read_csv(spamspa_path, encoding="utf-8")
    raw.columns = [column.strip() for column in raw.columns]
    is_spam = raw["tipo"].astype(str).str.strip().str.lower() == "spam"
    rows = []
    for row, message in raw.loc[is_spam, "mensaje"].fillna("").items():
        text = anonymize(str(message))
        label, reason = propose(text)
        rows.append(
            {
                "row": row,
                "text": text,
                "proposed": label,
                "label": label,
                "reason": reason,
            }
        )
    # ES: SpamSpa repite mensajes: se revisa cada texto una sola vez (la
    #     primera fila), que es la que conserva prepare() al quitar duplicados.
    # EN: SpamSpa repeats messages: each text is reviewed once (first row),
    #     which is the one prepare() keeps when dropping duplicates.
    return pd.DataFrame(rows).drop_duplicates(subset=["text"]).reset_index(drop=True)


if __name__ == "__main__":
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    review = build_review(source)
    review.to_csv(target, index=False, encoding="utf-8")
    counts = review["proposed"].value_counts().to_dict()
    print(f"{len(review)} mensajes para revisar. Propuesta: {counts}")
