"""Preparación de datos del clasificador de 3 clases (#36).
Data preparation for the 3-class classifier (#36).

ES: Clases alineadas con el semáforo de Avizor:
      none  → GREEN (legítimo)
      spam  → AMBER (publicidad o molestia)
      fraud → RED   (estafa)
    Fuentes:
      - SpaPhish (correos): solo el cuerpo. Label 0 → none, 1 → fraud.
      - SpamSpa (SMS): "ham" → none. "spam" → spam o fraud según la revisión
        manual (spamspa_review.csv), porque SpamSpa mezcla publicidad y estafas.
    Todo el texto se anonimiza igual que en el móvil antes de usarlo.
EN: Classes aligned with Avizor's traffic light (none/spam/fraud).
    Sources: SpaPhish (email body) and SpamSpa (SMS). SpamSpa "spam" is split
    into spam or fraud by the manual review (spamspa_review.csv).
    All text is anonymized like on the phone before use.
"""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.classifier.anonymize import anonymize

LABELS = ["none", "spam", "fraud"]
LABEL2ID = {label: index for index, label in enumerate(LABELS)}
RANDOM_STATE = 42


def load_spaphish(path: Path) -> pd.DataFrame:
    """ES: Solo el cuerpo: los SMS y notificaciones no tienen asunto.
    EN: Body only: SMS and notifications have no subject.
    """
    raw = pd.read_csv(path, encoding="utf-8")
    return pd.DataFrame(
        {
            "text": raw["body"].fillna("").astype(str),
            "label": raw["Label"].map({0: "none", 1: "fraud"}),
            "source": "spaphish",
        }
    )


def load_spamspa(path: Path, review_path: Path | None = None) -> pd.DataFrame:
    """ES: Las columnas son "mensaje" y " tipo" (con un espacio delante).
    Sin revisión, todo el spam cuenta como "spam" (AMBER).
    EN: Columns are "mensaje" and " tipo" (leading space).
    Without a review, all spam counts as "spam" (AMBER).
    """
    raw = pd.read_csv(path, encoding="utf-8")
    raw.columns = [column.strip() for column in raw.columns]
    tipo = raw["tipo"].astype(str).str.strip().str.lower()
    data = pd.DataFrame(
        {
            "text": raw["mensaje"].fillna("").astype(str),
            "label": tipo.map({"ham": "none", "spam": "spam"}),
            "source": "spamspa",
        }
    )
    if review_path is not None:
        review = pd.read_csv(review_path, encoding="utf-8")
        reviewed = review.set_index("row")["label"].str.strip().str.lower()
        invalid = set(reviewed.unique()) - {"spam", "fraud"}
        if invalid:
            raise ValueError(f"Etiquetas no válidas en la revisión: {invalid}")
        is_spam = data["label"] == "spam"
        data.loc[is_spam, "label"] = (
            data.index[is_spam].map(reviewed).fillna("spam").to_numpy()
        )
    return data


def prepare(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """ES: Une, anonimiza, quita vacíos y duplicados (tras anonimizar, para
    que dos mensajes iguales salvo un teléfono cuenten como uno).
    EN: Joins, anonymizes, drops empties and duplicates (after anonymizing,
    so two messages that only differ in a phone number count as one).
    """
    data = pd.concat(frames, ignore_index=True)
    data = data.dropna(subset=["label"])
    data["text"] = data["text"].map(anonymize).str.strip()
    data = data[data["text"] != ""]
    data = data.drop_duplicates(subset=["text"]).reset_index(drop=True)
    data["label_id"] = data["label"].map(LABEL2ID)
    return data


def split(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """ES: 70/15/15 estratificado por fuente y clase, con semilla fija.
    EN: 70/15/15 stratified by source and class, fixed seed.
    """
    strata = data["source"] + "/" + data["label"]
    train, rest = train_test_split(
        data, test_size=0.30, random_state=RANDOM_STATE, stratify=strata
    )
    val, test = train_test_split(
        rest,
        test_size=0.50,
        random_state=RANDOM_STATE,
        stratify=strata.loc[rest.index],
    )
    return {
        "train": train.reset_index(drop=True),
        "val": val.reset_index(drop=True),
        "test": test.reset_index(drop=True),
    }
