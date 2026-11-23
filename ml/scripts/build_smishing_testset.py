"""Extrae SMS de smishing reales del corpus INCIBE/OSI para armar el test set (#146).

ES: Vuelca los fragmentos de ChromaDB a un fichero de revisión manual (.txt) y,
    opcionalmente, intenta auto-detectar líneas con aspecto de SMS real citado
    en los avisos (cortas, entre comillas o tras "del tipo:", "como:", etc.).
    La revisión manual sigue siendo necesaria antes de usar el CSV como test set.

Uso / Usage:
    python scripts/build_smishing_testset.py \
        --chroma ../rag/chroma_db \
        --dump  data/raw/corpus_dump.txt          # paso 1: revisar manualmente
        [--csv  data/raw/smishing_real_test.csv]  # paso 2: guardar auto-detectados
"""

import argparse
import csv
import re
import sys
from pathlib import Path

_SMS_INTRO = re.compile(
    r"(del tipo|como|ejemplo|mensaje[^:]{0,20}:|sms[^:]{0,20}:|texto[^:]{0,20}:)\s*[\"«]?",
    re.I,
)
_QUOTED = re.compile(r'[\"«"]([^\"»"]{20,155})[\"»"]')


def load_corpus(chroma_path: Path) -> list[dict]:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_path))
    col = client.get_collection("official_notices")
    data = col.get(include=["documents", "metadatas"])
    return [
        {"text": doc.strip(), "source": meta.get("source", "unknown")}
        for doc, meta in zip(data["documents"], data["metadatas"])
    ]


def extract_candidate_sms(fragment: str) -> list[str]:
    candidates = []
    for match in _QUOTED.finditer(fragment):
        candidate = match.group(1).strip()
        if re.search(r"https?://|llamar|verificar|premio|paquete|cuenta|bloquea", candidate, re.I):
            candidates.append(candidate)
    for match in _SMS_INTRO.finditer(fragment):
        rest = fragment[match.end() : match.end() + 200]
        first_line = re.split(r"[.\n]", rest)[0].strip().strip('"«»"')
        if 20 <= len(first_line) <= 160:
            candidates.append(first_line)
    return list(dict.fromkeys(candidates))


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae test set smishing real de ChromaDB")
    parser.add_argument("--chroma", type=Path, required=True, help="Ruta al chroma_db")
    parser.add_argument("--dump", type=Path, required=True, help="Fichero .txt de volcado para revisión manual")
    parser.add_argument("--csv", type=Path, default=None, help="CSV de salida con candidatos auto-detectados")
    args = parser.parse_args()

    if not args.chroma.exists():
        sys.exit(f"ChromaDB no encontrado en {args.chroma}")

    print(f"Cargando corpus de {args.chroma}...")
    fragments = load_corpus(args.chroma)
    print(f"  {len(fragments)} fragmentos cargados.")

    args.dump.parent.mkdir(parents=True, exist_ok=True)
    candidates_all = []

    with args.dump.open("w", encoding="utf-8") as f:
        for i, frag in enumerate(fragments, 1):
            f.write(f"{'='*60}\n")
            f.write(f"[{i}/{len(fragments)}] FUENTE: {frag['source'].upper()}\n")
            f.write(f"{'='*60}\n")
            f.write(frag["text"] + "\n\n")
            candidates = extract_candidate_sms(frag["text"])
            if candidates:
                f.write(">>> CANDIDATOS AUTO-DETECTADOS:\n")
                for c in candidates:
                    f.write(f"  • {c}\n")
                    candidates_all.append({"text": c, "label": "fraud", "source": frag["source"]})
                f.write("\n")

    print(f"Volcado guardado en: {args.dump}")
    print(f"Revisa el fichero y anota los SMS reales que encuentres.")

    if args.csv and candidates_all:
        seen = set()
        unique = []
        for row in candidates_all:
            if row["text"] not in seen:
                seen.add(row["text"])
                unique.append(row)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["text", "label", "source"])
            writer.writeheader()
            writer.writerows(unique)
        print(f"{len(unique)} candidatos auto-detectados guardados en: {args.csv}")
        print("IMPORTANTE: revisa el CSV manualmente antes de usarlo como test set.")


if __name__ == "__main__":
    main()
