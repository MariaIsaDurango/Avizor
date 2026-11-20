"""Métricas del clasificador de 3 clases (sin torch, para poder testearlas).
3-class classifier metrics (no torch, so they can be tested).

ES: Lo más importante en Avizor es no dejar pasar una estafa: por eso se mira
    sobre todo el recall de "fraud". También se mide si un mensaje sospechoso
    (spam o fraud) se detecta como sospechoso, que es lo que decide si la app
    avisa o no.
EN: What matters most in Avizor is not letting a scam through, so "fraud"
    recall is the key metric. We also measure whether a suspicious message
    (spam or fraud) is detected as suspicious, which decides whether the app
    warns at all.
"""

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from src.classifier.data import LABEL2ID, LABELS

# ES: Objetivos del proyecto (#36). EN: Project targets (#36).
FRAUD_RECALL_TARGET = 0.95
SMS_SUSPICIOUS_RECALL_TARGET = 0.80


def class_metrics(y_true, y_pred) -> dict[str, float]:
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=list(range(len(LABELS))), zero_division=0
    )
    result: dict[str, float] = {}
    for index, label in enumerate(LABELS):
        result[f"{label}_precision"] = float(precision[index])
        result[f"{label}_recall"] = float(recall[index])
        result[f"{label}_f1"] = float(f1[index])
    result["macro_f1"] = float(np.mean(f1))
    result["accuracy"] = float(np.mean(y_true == y_pred))

    # ES: Sospechoso = spam o fraud. EN: Suspicious = spam or fraud.
    none_id = LABEL2ID["none"]
    suspicious = y_true != none_id
    detected = y_pred != none_id
    result["suspicious_recall"] = (
        float(np.mean(detected[suspicious])) if suspicious.any() else 0.0
    )
    # ES: Estafas que acaban como "none": el peor error (no se avisa).
    # EN: Scams predicted as "none": the worst error (no warning at all).
    fraud = y_true == LABEL2ID["fraud"]
    result["fraud_missed_as_none"] = int(np.sum(fraud & (y_pred == none_id)))
    return result


def confusion(y_true, y_pred) -> list[list[int]]:
    return confusion_matrix(y_true, y_pred, labels=list(range(len(LABELS)))).tolist()


def meets_targets(by_source: dict[str, dict[str, float]]) -> dict[str, bool]:
    """ES: Criterios de éxito del #36. EN: #36 success criteria."""
    email = by_source.get("spaphish", {})
    sms = by_source.get("spamspa", {})
    return {
        "email_fraud_recall_>=95%": email.get("fraud_recall", 0.0)
        >= FRAUD_RECALL_TARGET,
        "sms_suspicious_recall_>=80%": sms.get("suspicious_recall", 0.0)
        >= SMS_SUSPICIOUS_RECALL_TARGET,
    }
