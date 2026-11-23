"""Umbral de decisión para la clase "fraud" (#38).
Decision threshold for the "fraud" class (#38).

ES: El modelo devuelve una probabilidad por clase. En lugar de quedarnos
    siempre con la más alta, marcamos "fraud" cuando su probabilidad supera
    un umbral. Bajar el umbral detecta más estafas (más recall) a cambio de
    más falsos positivos. El umbral se elige con el conjunto de validación,
    nunca con el de test, para que las métricas de test sigan siendo honestas.
EN: The model returns one probability per class. Instead of always taking the
    highest one, we predict "fraud" when its probability passes a threshold.
    A lower threshold catches more scams (higher recall) at the cost of more
    false positives. It is chosen on the validation set, never on test, so
    test metrics stay honest.
"""

import numpy as np

from src.classifier.data import LABEL2ID

FRAUD_ID = LABEL2ID["fraud"]
# ES: Nunca por debajo de este valor, para no marcar todo como estafa.
# EN: Never below this value, so not everything is flagged as a scam.
MIN_THRESHOLD = 0.05
DEFAULT_THRESHOLD = 0.5


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def predict_with_threshold(probs: np.ndarray, threshold: float) -> np.ndarray:
    """ES: "fraud" si su probabilidad >= umbral; si no, la mejor entre none y spam.
    EN: "fraud" if its probability >= threshold; otherwise the best of none/spam.
    """
    probs = np.asarray(probs, dtype=float)
    others = probs.copy()
    others[:, FRAUD_ID] = -1.0
    predictions = np.argmax(others, axis=-1)
    predictions[probs[:, FRAUD_ID] >= threshold] = FRAUD_ID
    return predictions


def fraud_recall(y_true: np.ndarray, predictions: np.ndarray) -> float:
    fraud = np.asarray(y_true) == FRAUD_ID
    if not fraud.any():
        return 0.0
    return float(np.mean(np.asarray(predictions)[fraud] == FRAUD_ID))


def calibrate_fraud_threshold(
    probs: np.ndarray, y_true: np.ndarray, target_recall: float
) -> float:
    """ES: El umbral más alto que alcanza el recall objetivo en validación.
    Si ninguno lo alcanza, el umbral más alto con el mejor recall posible:
    bajar más solo añadiría falsos positivos sin detectar más estafas.
    EN: The highest threshold that reaches the target recall on validation.
    If none does, the highest threshold with the best reachable recall:
    going lower would only add false positives without catching more scams.
    """
    grid = np.round(np.arange(DEFAULT_THRESHOLD, MIN_THRESHOLD - 1e-9, -0.01), 2)
    recalls = [
        fraud_recall(y_true, predict_with_threshold(probs, float(t))) for t in grid
    ]
    for threshold, recall in zip(grid, recalls, strict=True):
        if recall >= target_recall:
            return float(threshold)
    best = max(recalls)
    return float(next(t for t, r in zip(grid, recalls, strict=True) if r == best))
