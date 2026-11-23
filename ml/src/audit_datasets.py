from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "ml" / "data" / "raw"


def load_csv(file_path: Path, separator: str = ",") -> pd.DataFrame:
    """Carga un CSV probando distintas codificaciones habituales."""
    encodings = ["utf-8", "utf-8-sig", "latin-1"]

    for encoding in encodings:
        try:
            return pd.read_csv(
                file_path,
                sep=separator,
                encoding=encoding
            )
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not read file: {file_path}")


def audit_dataset(
    name: str,
    file_path: Path,
    label_column: str,
    separator: str = ","
) -> pd.DataFrame:
    """Muestra estadísticas de calidad sin imprimir contenido de mensajes."""

    print("\\n" + "=" * 65)
    print(f"DATASET: {name}")
    print("=" * 65)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found: {file_path}")

    df = load_csv(file_path, separator)

    print(f"\\nRows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")
    print("\\nColumn names:")
    print(df.columns.tolist())

    print("\\nData types:")
    print(df.dtypes.to_string())

    print("\\nMissing values:")
    missing = df.isnull().sum()
    print(missing[missing > 0].to_string() if missing.any() else "No missing values")

    print("\\nExact duplicate rows:")
    print(df.duplicated().sum())

    if label_column in df.columns:
        print(f"\\nLabel distribution ({label_column}):")
        print(df[label_column].value_counts(dropna=False).to_string())
        print("\\nLabel percentages:")
        print(
            (df[label_column].value_counts(normalize=True, dropna=False) * 100)
            .round(2)
            .to_string()
        )
    else:
        raise KeyError(f"Label column '{label_column}' not found in {name}")

    return df


def compare_train_test(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    text_column: str = "text"
) -> None:
    """Comprueba el solapamiento de textos sin mostrar los mensajes."""

    print("\\n" + "=" * 65)
    print("TRAIN / TEST COMPARISON")
    print("=" * 65)

    if text_column not in train_df.columns or text_column not in test_df.columns:
        raise KeyError(f"Text column '{text_column}' must exist in both datasets")

    train_texts = set(
        train_df[text_column].dropna().astype(str).str.strip().str.lower()
    )
    test_texts = set(
        test_df[text_column].dropna().astype(str).str.strip().str.lower()
    )
    overlap = train_texts.intersection(test_texts)

    print(f"Unique texts in train: {len(train_texts)}")
    print(f"Unique texts in test: {len(test_texts)}")
    print(f"Texts appearing in both: {len(overlap)}")
    print(
        "Percentage of unique test texts overlapping with train: "
        f"{(len(overlap) / len(test_texts) * 100):.2f}%"
        if test_texts else "No test texts available"
    )


def main() -> None:
    """Ejecuta la auditoría inicial de SpaPhish y SpamSpa."""

    audit_dataset(
        name="SpaPhish",
        file_path=RAW_DATA_DIR / "spaphish" / "Spaphish dataset - DiB.csv",
        label_column="Label",
        separator=","
    )

    spamspa_train = audit_dataset(
        name="SpamSpa - Train",
        file_path=RAW_DATA_DIR / "spamspa" / "train.csv",
        label_column="label"
    )

    spamspa_test = audit_dataset(
        name="SpamSpa - Test",
        file_path=RAW_DATA_DIR / "spamspa" / "test.csv",
        label_column="label"
    )

    compare_train_test(spamspa_train, spamspa_test)


if __name__ == "__main__":
    main()
