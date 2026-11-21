"""Fine-tuning de RoBERTa-BNE para 3 clases: none / spam / fraud (#36).
Fine-tuning RoBERTa-BNE for 3 classes: none / spam / fraud (#36).

ES: Pensado para ejecutarse en Google Colab con GPU (notebook 04). Guarda en
    --out el modelo, el tokenizador, los splits anonimizados y metrics.json.
    Uso:
      python -m src.classifier.train \\
          --spaphish "data/raw/spaphish/Spaphish dataset - DiB.csv" \\
          --spamspa data/raw/spamspa/train.csv \\
          --review data/raw/spamspa/spamspa_review.csv \\
          --out models/roberta-3c
EN: Meant to run on Google Colab with a GPU (notebook 04). Saves the model,
    tokenizer, anonymized splits and metrics.json in --out.
"""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from torch import nn
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
    set_seed,
)

from src.classifier.anonymize import NER_MODEL_VERSION
from src.classifier.data import (
    LABEL2ID,
    LABELS,
    RANDOM_STATE,
    load_spamspa,
    load_spaphish,
    prepare,
    split,
)
from src.classifier.metrics import class_metrics, confusion, meets_targets

# ES: Se prueba en orden; los pesos de PlanTL se han movido de cuenta varias veces.
# EN: Tried in order; PlanTL weights have moved between accounts several times.
CANDIDATE_MODELS = [
    "PlanTL-GOB-ES/roberta-base-bne",
    "BSC-LT/roberta-base-bne",
    "dccuchile/bert-base-spanish-wwm-cased",
]


class WeightedTrainer(Trainer):
    """ES: Pesa más los errores en "fraud" para priorizar su recall.
    EN: Weighs "fraud" errors more to prioritise its recall.
    """

    def __init__(self, *args, class_weights: torch.Tensor, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss_fn = nn.CrossEntropyLoss(
            weight=self.class_weights.to(outputs.logits.device)
        )
        loss = loss_fn(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


def load_base_model(name: str | None):
    names = [name] if name else CANDIDATE_MODELS
    last_error = None
    for candidate in names:
        try:
            tokenizer = AutoTokenizer.from_pretrained(candidate)
            model = AutoModelForSequenceClassification.from_pretrained(
                candidate,
                num_labels=len(LABELS),
                id2label=dict(enumerate(LABELS)),
                label2id=LABEL2ID,
                # ES: Por si el modelo base ya trae otra cabeza de clasificación.
                # EN: In case the base model already has another classifier head.
                ignore_mismatched_sizes=True,
            )
            print(f"Modelo base: {candidate}")
            return candidate, tokenizer, model
        # ES: OSError = no existe o sin pesos; ValueError = tokenizer incompleto.
        # EN: OSError = missing repo or weights; ValueError = broken tokenizer.
        except (OSError, ValueError) as error:
            print(f"No disponible: {candidate} ({error.__class__.__name__})")
            last_error = error
    raise RuntimeError("Ningún modelo base disponible") from last_error


def to_dataset(frame: pd.DataFrame, tokenizer, max_length: int) -> Dataset:
    dataset = Dataset.from_pandas(
        frame[["text", "label_id"]].rename(columns={"label_id": "labels"}),
        preserve_index=False,
    )
    return dataset.map(
        lambda batch: tokenizer(batch["text"], truncation=True, max_length=max_length),
        batched=True,
        remove_columns=["text"],
    )


def predict(trainer: Trainer, dataset: Dataset) -> np.ndarray:
    return np.argmax(trainer.predict(dataset).predictions, axis=-1)


def measure_latency(model, tokenizer, texts: list[str], max_length: int) -> float:
    """ES: Milisegundos por mensaje en CPU, de uno en uno (como en la API).
    EN: Milliseconds per message on CPU, one at a time (like the API).
    """
    model = model.to("cpu").eval()
    timings = []
    with torch.no_grad():
        for text in texts:
            start = time.perf_counter()
            inputs = tokenizer(
                text, truncation=True, max_length=max_length, return_tensors="pt"
            )
            model(**inputs)
            timings.append((time.perf_counter() - start) * 1000)
    return float(np.median(timings))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spaphish", type=Path, required=True)
    parser.add_argument("--spamspa", type=Path, required=True)
    parser.add_argument("--review", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--fraud-weight", type=float, default=2.0)
    args = parser.parse_args()

    set_seed(RANDOM_STATE)
    args.out.mkdir(parents=True, exist_ok=True)

    data = prepare(
        [load_spaphish(args.spaphish), load_spamspa(args.spamspa, args.review)]
    )
    parts = split(data)
    for name, frame in parts.items():
        frame.to_csv(args.out / f"{name}.csv", index=False)
    print(pd.crosstab(data["source"], data["label"]))

    base_name, tokenizer, model = load_base_model(args.model)
    datasets = {
        name: to_dataset(frame, tokenizer, args.max_length)
        for name, frame in parts.items()
    }

    weights = torch.ones(len(LABELS))
    weights[LABEL2ID["fraud"]] = args.fraud_weight

    def compute_metrics(prediction):
        logits, labels = prediction
        return class_metrics(labels, np.argmax(logits, axis=-1))

    # ES: 10 % de pasos de calentamiento. warmup_steps existe en transformers
    #     4 y 5 (warmup_ratio ya no está en la 5).
    # EN: 10 % warm-up steps. warmup_steps exists in transformers 4 and 5.
    steps_per_epoch = -(-len(datasets["train"]) // args.batch_size)
    warmup_steps = int(steps_per_epoch * args.epochs * 0.1)

    training_args = TrainingArguments(
        output_dir=str(args.out / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_steps=warmup_steps,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        fp16=torch.cuda.is_available(),
        report_to="none",
        seed=RANDOM_STATE,
    )
    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=datasets["train"],
        eval_dataset=datasets["val"],
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
        class_weights=weights,
    )
    trainer.train()

    # ES: Evaluación final en test, total y por fuente (correo / SMS).
    # EN: Final test evaluation, overall and per source (email / SMS).
    test = parts["test"]
    predictions = predict(trainer, datasets["test"])
    by_source = {}
    for source in sorted(test["source"].unique()):
        mask = (test["source"] == source).to_numpy()
        by_source[source] = class_metrics(
            test["label_id"].to_numpy()[mask], predictions[mask]
        )

    version = f"roberta-3c-{datetime.now(UTC):%Y%m%d}"
    sample = test["text"].sample(min(50, len(test)), random_state=RANDOM_STATE)
    report = {
        "model_version": version,
        "base_model": base_name,
        "labels": LABELS,
        "ner_model_version": NER_MODEL_VERSION,
        "max_length": args.max_length,
        "sizes": {name: len(frame) for name, frame in parts.items()},
        "test": class_metrics(test["label_id"], predictions),
        "test_by_source": by_source,
        "confusion_test": confusion(test["label_id"], predictions),
        "targets": meets_targets(by_source),
        "cpu_latency_ms_median": measure_latency(
            trainer.model, tokenizer, sample.tolist(), args.max_length
        ),
    }

    final_dir = args.out / "model"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    (args.out / "metrics.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
