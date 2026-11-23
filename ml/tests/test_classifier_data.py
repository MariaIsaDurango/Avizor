"""Tests de datos y anonimización del clasificador (#36). Sin descargas.
Classifier data and anonymization tests (#36). No downloads.

ES: Todos los mensajes son inventados. EN: All messages are made up.
"""

import pandas as pd
import pytest

from src.classifier.anonymize import anonymize
from src.classifier.data import (
    LABEL2ID,
    LABELS,
    build_splits,
    load_spamspa,
    load_spaphish,
    load_synthetic,
    prepare,
    split,
)
from src.classifier.review import build_review, propose

# ---------- Anonimización igual que el móvil / same as the phone ----------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Tu IBAN ES12 1234 5678 9012 3456 7890", "Tu IBAN [IBAN]"),
        # ES: El patrón del móvil también se come el espacio final; se copia tal cual.
        # EN: The phone's pattern also eats the trailing space; copied as is.
        ("Tarjeta 4111 1111 1111 1111 caducada", "Tarjeta [CARD]caducada"),
        ("DNI 12345678Z", "DNI [ID_NUMBER]"),
        ("Escribe a ana.lopez@example.com", "Escribe a [EMAIL]"),
        ("Llama al +34 600 000 000", "Llama al [PHONE]"),
        ("Vivo en Calle Mayor 5, 3 izq", "Vivo en [ADDRESS] izq"),
    ],
)
def test_same_markers_as_mobile(raw, expected):
    assert anonymize(raw) == expected


def test_urls_are_kept_like_on_the_phone():
    text = "Verifica en http://banco-seguro.top/login ahora"
    assert anonymize(text) == text


def test_empty_text():
    assert anonymize("") == ""


# ---------- Carga y preparación / loading and preparation ----------


@pytest.fixture
def spaphish_csv(tmp_path):
    path = tmp_path / "spaphish.csv"
    pd.DataFrame(
        {
            "subject": ["Hola", "Urgente", "Factura", "Aviso"],
            "body": [
                "Nos vemos el domingo",
                "Su cuenta está bloqueada, llame al 600 000 000",
                "Adjunto la factura de noviembre",
                "Su cuenta está bloqueada, llame al 611 111 111",
            ],
            "Label": [0, 1, 0, 1],
        }
    ).to_csv(path, index=False)
    return path


@pytest.fixture
def spamspa_csv(tmp_path):
    path = tmp_path / "spamspa.csv"
    pd.DataFrame(
        {
            "mensaje": [
                "Ya llegué a casa",
                "Oferta 50% en tarifas de fibra",
                "Ha ganado un premio, confirme su cuenta",
            ],
            " tipo": ["ham", " spam", "spam"],
        }
    ).to_csv(path, index=False)
    return path


def test_spaphish_uses_body_and_maps_labels(spaphish_csv):
    data = load_spaphish(spaphish_csv)
    assert data["label"].tolist() == ["none", "fraud", "none", "fraud"]
    assert "Hola" not in data["text"].iloc[0]


def test_spamspa_without_review_is_all_spam(spamspa_csv):
    data = load_spamspa(spamspa_csv)
    assert data["label"].tolist() == ["none", "spam", "spam"]


def test_spamspa_review_splits_spam_and_fraud(spamspa_csv, tmp_path):
    review = tmp_path / "review.csv"
    pd.DataFrame({"row": [1, 2], "label": ["spam", " Fraud "]}).to_csv(
        review, index=False
    )
    data = load_spamspa(spamspa_csv, review)
    assert data["label"].tolist() == ["none", "spam", "fraud"]


def test_invalid_review_label_fails(spamspa_csv, tmp_path):
    review = tmp_path / "review.csv"
    pd.DataFrame({"row": [1], "label": ["estafa"]}).to_csv(review, index=False)
    with pytest.raises(ValueError):
        load_spamspa(spamspa_csv, review)


def test_prepare_anonymizes_and_dedupes(spaphish_csv, spamspa_csv):
    data = prepare([load_spaphish(spaphish_csv), load_spamspa(spamspa_csv)])
    # ES: Los dos "cuenta bloqueada" solo difieren en el teléfono → uno.
    # EN: The two "account blocked" only differ in the phone → one.
    blocked = data[data["text"].str.contains("bloqueada")]
    assert len(blocked) == 1
    assert "[PHONE]" in blocked["text"].iloc[0]
    assert set(data["label"]) <= set(LABELS)
    assert (data["label_id"] == data["label"].map(LABEL2ID)).all()


def test_split_is_stratified_and_disjoint():
    rows = []
    for source in ["spaphish", "spamspa"]:
        for label in LABELS:
            for index in range(20):
                rows.append(
                    {
                        "text": f"{source} {label} {index}",
                        "label": label,
                        "source": source,
                    }
                )
    data = pd.DataFrame(rows)
    parts = split(data)
    assert [len(parts[name]) for name in ("train", "val", "test")] == [84, 18, 18]
    texts = [set(parts[name]["text"]) for name in ("train", "val", "test")]
    assert not (texts[0] & texts[1] or texts[0] & texts[2] or texts[1] & texts[2])
    for name in ("train", "val", "test"):
        assert set(parts[name]["label"]) == set(LABELS)


# ---------- Revisión de SpamSpa / SpamSpa review ----------


def test_propose_fraud_vs_ad():
    assert propose("Ha ganado un premio, confirme su cuenta")[0] == "fraud"
    assert propose("Oferta 50% en tarifas de fibra")[0] == "spam"


def test_build_review_only_spam_and_anonymized(tmp_path):
    path = tmp_path / "spamspa.csv"
    pd.DataFrame(
        {
            "mensaje": ["Hola", "Premio! llame al 600 000 000"],
            " tipo": ["ham", "spam"],
        }
    ).to_csv(path, index=False)
    review = build_review(path)
    assert review["row"].tolist() == [1]
    assert review["text"].iloc[0] == "Premio! llame al [PHONE]"
    assert review["label"].iloc[0] == review["proposed"].iloc[0]


# ---------- Métricas / metrics ----------


def test_metrics_fraud_recall_and_missed():
    from src.classifier.metrics import class_metrics, meets_targets

    none, spam, fraud = (LABEL2ID[label] for label in LABELS)
    y_true = [none, none, spam, fraud, fraud, fraud, fraud]
    y_pred = [none, spam, spam, fraud, fraud, spam, none]
    result = class_metrics(y_true, y_pred)
    assert result["fraud_recall"] == 0.5
    assert result["fraud_missed_as_none"] == 1
    # ES: 5 sospechosos, 4 detectados como no-none. EN: 5 suspicious, 4 flagged.
    assert result["suspicious_recall"] == 0.8
    targets = meets_targets({"spaphish": result, "spamspa": result})
    assert targets == {
        "email_fraud_recall_>=95%": False,
        "sms_suspicious_recall_>=80%": True,
    }


def test_build_review_reviews_each_text_once(tmp_path):
    path = tmp_path / "spamspa.csv"
    pd.DataFrame(
        {
            "mensaje": ["Premio gratis", "Hola", "Premio gratis"],
            " tipo": ["spam", "ham", "spam"],
        }
    ).to_csv(path, index=False)
    assert build_review(path)["row"].tolist() == [0]


def write_synthetic(tmp_path, rows):
    path = tmp_path / "synthetic.csv"
    pd.DataFrame(rows, columns=["text", "label", "source"]).to_csv(path, index=False)
    return path


def test_load_synthetic_reads_labels_and_source(tmp_path):
    path = write_synthetic(tmp_path, [["Paga aquí https://x-fake.es", "fraud", "groq"]])
    frame = load_synthetic(path)
    assert frame.loc[0, "label"] == "fraud"
    assert frame.loc[0, "source"] == "groq"


def test_load_synthetic_rejects_unknown_labels(tmp_path):
    path = write_synthetic(tmp_path, [["Hola", "phishing", "groq"]])
    with pytest.raises(ValueError):
        load_synthetic(path)


def test_load_synthetic_rejects_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"mensaje": ["Hola"], " tipo": ["ham"]}).to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_synthetic(path)


def real_frames():
    rows = [(f"mensaje normal {i}", "none") for i in range(40)]
    rows += [(f"estafa real {i}", "fraud") for i in range(40)]
    return [
        pd.DataFrame(
            {
                "text": [t for t, _ in rows],
                "label": [lab for _, lab in rows],
                "source": "real",
            }
        )
    ]


def test_synthetic_rows_go_to_train_only_and_real_splits_do_not_change(tmp_path):
    baseline = build_splits(real_frames())
    synthetic = load_synthetic(
        write_synthetic(
            tmp_path,
            [
                [f"Paga la multa {i} en https://dgt-falsa.es", "fraud", "groq"]
                for i in range(10)
            ]
            + [["estafa real 3", "fraud", "groq"]],  # ES: repite un texto real
        )
    )
    parts = build_splits(real_frames(), [synthetic])
    for name in ("val", "test"):
        assert parts[name].equals(baseline[name])
        assert (parts[name]["source"] != "groq").all()
    # ES: 10 sintéticos únicos: 8 a train y 2 a synthetic_test (20 %).
    added = parts["train"][parts["train"]["source"] == "groq"]
    assert len(added) == 8
    assert len(parts["train"]) == len(baseline["train"]) + 8
    assert len(parts["synthetic_test"]) == 2
    assert not set(parts["synthetic_test"]["text"]) & set(parts["train"]["text"])


def test_load_synthetic_reads_ham_as_none(tmp_path):
    path = write_synthetic(tmp_path, [["Su cita es mañana https://x.es", "ham", "legit"]])
    assert load_synthetic(path).loc[0, "label"] == "none"
