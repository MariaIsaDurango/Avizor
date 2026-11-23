"""Exporta el modelo de 3 clases a ONNX int8 y calibra el umbral de fraud (#38).
Exports the 3-class model to ONNX int8 and calibrates the fraud threshold (#38).

ES: El backend no usa torch: carga model.int8.onnx con onnxruntime y
    tokenizer.json con la librería tokenizers. Este script:
      1. Reconstruye los mismos splits que train.py (misma semilla).
      2. Exporta el modelo a ONNX y lo cuantiza a int8 (más pequeño y rápido).
      3. Elige el umbral de fraud con validación y mide test con ese umbral.
      4. Guarda en --out todo lo que necesita el backend.
    Uso:
      python -m src.classifier.export \\
          --model-dir models/avizor-3c/model \\
          --spaphish "data/raw/spaphish/Spaphish dataset - DiB.csv" \\
          --spamspa data/raw/spamspa/train.csv \\
          --review data/raw/spamspa/spamspa_review.csv \\
          --out models/avizor-3c-onnx
EN: The backend does not use torch: it loads model.int8.onnx with onnxruntime
    and tokenizer.json with the tokenizers library. This script rebuilds the
    train.py splits, exports and quantizes the model, calibrates the fraud
    threshold on validation, evaluates test and saves the backend bundle.
"""

import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from tokenizers import Tokenizer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.classifier.anonymize import NER_MODEL_VERSION
from src.classifier.data import (
    LABEL2ID,
    LABELS,
    build_splits,
    load_spamspa,
    load_spaphish,
    load_synthetic,
    prepare,
)
from src.classifier.metrics import (
    FRAUD_RECALL_TARGET,
    class_metrics,
    confusion,
    meets_targets,
)
from src.classifier.thresholds import (
    calibrate_fraud_threshold,
    predict_with_threshold,
    softmax,
)

ONNX_FP32 = "model.onnx"
ONNX_INT8 = "model.int8.onnx"
CONFIG_FILE = "avizor_classifier.json"
# ES: Textos de distinta longitud para comprobar que ONNX da lo mismo que torch.
# EN: Texts of different lengths to check that ONNX matches torch.
PARITY_TEXTS = [
    "Hola",
    "Su cuenta ha sido bloqueada, entre en el enlace para verificar sus datos.",
    "Oferta exclusiva: 50% de descuento en toda la tienda solo este fin de semana",
]


def export_onnx(model_dir: Path, out_dir: Path, max_length: int) -> np.ndarray:
    """ES: Exporta a ONNX (fp32) con longitud y lote variables.
    EN: Exports to ONNX (fp32) with dynamic batch and sequence length.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    # ES: "eager" y un lote con relleno, para que la máscara de atención quede
    #     en el grafo y no como constante del ejemplo.
    # EN: "eager" and a padded batch, so the attention mask stays in the graph
    #     instead of being frozen from the example.
    model = AutoModelForSequenceClassification.from_pretrained(
        model_dir, attn_implementation="eager"
    ).eval()
    sample = tokenizer(
        PARITY_TEXTS,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    input_names = list(sample.keys())
    dynamic_axes = {name: {0: "batch", 1: "sequence"} for name in input_names}
    dynamic_axes["logits"] = {0: "batch"}

    class LogitsOnly(torch.nn.Module):
        def __init__(self, wrapped):
            super().__init__()
            self.wrapped = wrapped

        def forward(self, *args):
            return self.wrapped(**dict(zip(input_names, args, strict=True))).logits

    with torch.no_grad():
        expected = softmax(model(**sample).logits.numpy())
        torch.onnx.export(
            LogitsOnly(model),
            tuple(sample[name] for name in input_names),
            str(out_dir / ONNX_FP32),
            input_names=input_names,
            output_names=["logits"],
            dynamic_axes=dynamic_axes,
            opset_version=17,
            dynamo=False,
        )
    # ES: El backend solo necesita tokenizer.json. EN: Backend only needs tokenizer.json.
    tokenizer.save_pretrained(out_dir / "tokenizer")
    shutil.copy(out_dir / "tokenizer" / "tokenizer.json", out_dir / "tokenizer.json")
    shutil.rmtree(out_dir / "tokenizer")
    return expected


class OnnxModel:
    """ES: Igual que lo usará el backend. EN: Same as the backend will use it."""

    def __init__(self, onnx_path: Path, tokenizer_path: Path, max_length: int):
        self.session = ort.InferenceSession(
            str(onnx_path), providers=["CPUExecutionProvider"]
        )
        self.input_names = [item.name for item in self.session.get_inputs()]
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length)

    def probabilities(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        self.tokenizer.enable_padding()
        chunks = []
        for start in range(0, len(texts), batch_size):
            encodings = self.tokenizer.encode_batch(texts[start : start + batch_size])
            chunks.append(softmax(self.session.run(None, self._feed(encodings))[0]))
        self.tokenizer.no_padding()
        return np.concatenate(chunks)

    def _feed(self, encodings) -> dict[str, np.ndarray]:
        columns = {
            "input_ids": [e.ids for e in encodings],
            "attention_mask": [e.attention_mask for e in encodings],
            "token_type_ids": [e.type_ids for e in encodings],
        }
        return {
            name: np.asarray(columns[name], dtype=np.int64) for name in self.input_names
        }

    def latency_ms(self, texts: list[str]) -> float:
        """ES: Tokenizado + inferencia, de uno en uno, como en el backend.
        EN: Tokenization + inference, one at a time, as in the backend.
        """
        timings = []
        for text in texts:
            start = time.perf_counter()
            encoding = self.tokenizer.encode(text)
            self.session.run(None, self._feed([encoding]))
            timings.append((time.perf_counter() - start) * 1000)
        return float(np.median(timings))


def evaluate(frame, predictions: np.ndarray) -> dict:
    y_true = frame["label_id"].to_numpy()
    by_source = {}
    for source in sorted(frame["source"].unique()):
        mask = (frame["source"] == source).to_numpy()
        by_source[source] = class_metrics(y_true[mask], predictions[mask])
    return {
        "all": class_metrics(y_true, predictions),
        "by_source": by_source,
        "confusion": confusion(y_true, predictions),
        "targets": meets_targets(by_source),
    }


def extra_test(frame, probs: np.ndarray, threshold: float) -> dict:
    """ES: Estafas detectadas y legítimos marcados como estafa, con umbral.
    EN: Scams detected and legitimate messages flagged as scam, with threshold.
    """
    predictions = predict_with_threshold(probs, threshold)
    y_true = frame["label_id"].to_numpy()
    fraud, none = LABEL2ID["fraud"], LABEL2ID["none"]
    return {
        "messages": len(frame),
        "by_label": frame["label"].value_counts().to_dict(),
        "fraud_detected": int(((y_true == fraud) & (predictions == fraud)).sum()),
        "legit_flagged_as_fraud": int(
            ((y_true == none) & (predictions == fraud)).sum()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--spaphish", type=Path, required=True)
    parser.add_argument("--spamspa", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=None)
    # ES: SMS sintéticos (#146), solo para entrenar. EN: Synthetic SMS, train only.
    parser.add_argument("--synthetic", type=Path, action="append", default=[])
    parser.add_argument("--real-test", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target-recall", type=float, default=FRAUD_RECALL_TARGET)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    training = json.loads((args.model_dir.parent / "metrics.json").read_text("utf-8"))
    max_length = training["max_length"]

    parts = build_splits(
        [load_spaphish(args.spaphish), load_spamspa(args.spamspa, args.review)],
        [load_synthetic(path) for path in args.synthetic],
    )
    if {k: len(v) for k, v in parts.items()} != training["sizes"]:
        raise SystemExit(
            "Los splits no coinciden con el entrenamiento: revisa los CSV y --synthetic."
        )

    expected = export_onnx(args.model_dir, args.out, max_length)
    quantize_dynamic(
        str(args.out / ONNX_FP32),
        str(args.out / ONNX_INT8),
        weight_type=QuantType.QInt8,
    )

    tokenizer_path = args.out / "tokenizer.json"
    fp32 = OnnxModel(args.out / ONNX_FP32, tokenizer_path, max_length)
    int8 = OnnxModel(args.out / ONNX_INT8, tokenizer_path, max_length)
    parity = float(np.abs(fp32.probabilities(PARITY_TEXTS) - expected).max())
    if parity > 1e-3:
        raise SystemExit(f"ONNX no coincide con torch (diferencia {parity:.4f}).")
    val, test = parts["val"], parts["test"]

    # ES: El umbral se calibra con el modelo int8, que es el que se despliega.
    # EN: The threshold is calibrated with the int8 model, the one deployed.
    val_probs = int8.probabilities(val["text"].tolist())
    threshold = calibrate_fraud_threshold(
        val_probs, val["label_id"].to_numpy(), args.target_recall
    )
    test_fp32 = fp32.probabilities(test["text"].tolist())
    test_int8 = int8.probabilities(test["text"].tolist())

    sample = test["text"].sample(min(50, len(test)), random_state=0).tolist()
    version = f"{training['model_version']}-onnx-int8"
    config = {
        "model_version": version,
        "base_model": training["base_model"],
        "labels": LABELS,
        "max_length": max_length,
        "fraud_threshold": threshold,
        "ner_model_version": NER_MODEL_VERSION,
        "onnx_file": ONNX_INT8,
        "tokenizer_file": "tokenizer.json",
    }
    report = {
        "model_version": version,
        "target_recall": args.target_recall,
        "fraud_threshold": threshold,
        "val_threshold_int8": evaluate(
            val, predict_with_threshold(val_probs, threshold)
        ),
        "test_argmax_fp32": evaluate(test, test_fp32.argmax(-1)),
        "test_argmax_int8": evaluate(test, test_int8.argmax(-1)),
        "test_threshold_int8": evaluate(
            test, predict_with_threshold(test_int8, threshold)
        ),
        "onnx_vs_torch_max_diff": parity,
        "int8_vs_fp32_agreement": float(
            np.mean(test_int8.argmax(-1) == test_fp32.argmax(-1))
        ),
        "size_mb": {
            name: round((args.out / name).stat().st_size / 1e6, 1)
            for name in (ONNX_FP32, ONNX_INT8)
        },
        "cpu_latency_ms_median": {
            "fp32": fp32.latency_ms(sample),
            "int8": int8.latency_ms(sample),
        },
    }
    extra = {}
    if "synthetic_test" in parts:
        frame = parts["synthetic_test"]
        extra["synthetic_test"] = extra_test(
            frame, int8.probabilities(frame["text"].tolist()), threshold
        )
    if args.real_test:
        frame = prepare([load_synthetic(path) for path in args.real_test])
        extra["real_test"] = extra_test(
            frame, int8.probabilities(frame["text"].tolist()), threshold
        )
    report["extra_tests_threshold_int8"] = extra
    (args.out / ONNX_FP32).unlink()  # ES: solo se despliega int8 / EN: only int8 ships
    (args.out / CONFIG_FILE).write_text(json.dumps(config, indent=2), "utf-8")
    (args.out / "metrics_onnx.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), "utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
