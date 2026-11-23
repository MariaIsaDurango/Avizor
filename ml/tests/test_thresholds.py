import numpy as np
import pytest
from src.classifier.data import LABEL2ID
from src.classifier.thresholds import (
    MIN_THRESHOLD,
    calibrate_fraud_threshold,
    fraud_recall,
    predict_with_threshold,
    softmax,
)

NONE, SPAM, FRAUD = LABEL2ID["none"], LABEL2ID["spam"], LABEL2ID["fraud"]


def test_softmax_rows_sum_to_one():
    probs = softmax(np.array([[1.0, 2.0, 3.0], [1000.0, 0.0, 0.0]]))
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert probs[1, 0] == pytest.approx(1.0)


def test_fraud_wins_when_above_threshold_even_if_not_highest():
    probs = np.array([[0.6, 0.0, 0.4]])
    assert predict_with_threshold(probs, 0.3).tolist() == [FRAUD]
    assert predict_with_threshold(probs, 0.5).tolist() == [NONE]


def test_below_threshold_picks_best_of_none_and_spam():
    probs = np.array([[0.2, 0.35, 0.45]])
    assert predict_with_threshold(probs, 0.5).tolist() == [SPAM]


def test_fraud_recall_without_fraud_is_zero():
    assert fraud_recall(np.array([NONE, SPAM]), np.array([NONE, SPAM])) == 0.0


def test_calibration_returns_highest_threshold_meeting_target():
    probs = np.array(
        [
            [0.1, 0.1, 0.8],  # fraud, easy
            [0.6, 0.1, 0.3],  # fraud, only caught with threshold <= 0.3
            [0.9, 0.05, 0.05],  # none
        ]
    )
    y_true = np.array([FRAUD, FRAUD, NONE])
    assert calibrate_fraud_threshold(probs, y_true, 1.0) == pytest.approx(0.3)
    assert calibrate_fraud_threshold(probs, y_true, 0.5) == pytest.approx(0.5)


def test_calibration_falls_back_to_minimum():
    probs = np.array([[0.98, 0.0, 0.02]])
    assert calibrate_fraud_threshold(probs, np.array([FRAUD]), 1.0) == MIN_THRESHOLD
