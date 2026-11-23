"""Genera SMS de smishing sintéticos en español usando ChromaDB + Groq (#146).

ES: Lee el corpus de avisos oficiales (INCIBE, OSI, Banco de España) de ChromaDB
    y lo usa como contexto para que Groq genere ejemplos de smishing realistas
    en español de España. La salida es un CSV compatible con load_spamspa().

EN: Reads the official-notices corpus (INCIBE, OSI, Banco de España) from
    ChromaDB and uses it as context for Groq to generate realistic Spanish
    smishing examples. Output is a CSV compatible with load_spamspa().

Uso / Usage:
    GROQ_API_KEY=sk-... python scripts/generate_smishing.py \
        --chroma ../../rag/chroma_db \
        --out data/raw/smishing_groq.csv \
        [--per-entity 10] [--model llama3-70b-8192]
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

ENTITIES = [
    "Correos de España",
    "Banco Santander",
    "BBVA",
    "CaixaBank",
    "Agencia Tributaria (AEAT / Hacienda)",
    "Dirección General de Tráfico (DGT)",
    "Seguridad Social",
    "Iberdrola",
    "Policía Nacional",
    "Amazon España",
]

SYSTEM = (
    "Eres un generador de datos de entrenamiento para un detector de fraude por SMS. "
    "Tu tarea es crear ejemplos realistas de smishing en español de España. "
    "Reglas estrictas:\n"
    "- Menos de 160 caracteres por SMS.\n"
    "- Suplanta siempre la entidad indicada.\n"
    "- Tono urgente: amenaza, multa pendiente, paquete retenido, cuenta bloqueada, etc.\n"
    "- Incluye un enlace falso (ej: https://correos-entrega.com/seguimiento).\n"
    "- Español natural de España (tuteo o ustedeo, vocabulario peninsular).\n"
    "- Sin saludos de email ('Estimado cliente', 'Buenos días', etc.).\n"
    "- Cada SMS debe tener un gancho distinto (multa, paquete, cuenta, verificación, premio…).\n"
    "- No empieces ninguna línea con número seguido de punto o paréntesis.\n"
    "- Devuelve SOLO los SMS, uno por línea, sin numeración, sin comillas, sin explicaciones."
)


def load_corpus(chroma_path: Path) -> list[str]:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_path))
    col = client.get_collection("official_notices")
    data = col.get(include=["documents", "metadatas"])
    docs = []
    for doc, meta in zip(data["documents"], data["metadatas"]):
        source = meta.get("source", "")
        docs.append(f"[{source.upper()}] {doc.strip()}")
    return docs


def select_context(corpus: list[str], entity: str, max_chars: int = 3000) -> str:
    keywords = entity.lower().replace("(", "").replace(")", "").replace("/", " ").split()
    scored = []
    for doc in corpus:
        score = sum(1 for kw in keywords if kw in doc.lower())
        # ES: Priorizar documentos con smishing, SMS, fraude, estafa.
        for trigger in ("smishing", "sms", "fraude", "estafa", "enlace", "phishing"):
            if trigger in doc.lower():
                score += 1
        scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    context, total = [], 0
    for _, doc in scored:
        if total + len(doc) > max_chars:
            break
        context.append(doc)
        total += len(doc)
    return "\n\n".join(context)


def generate_for_entity(
    client, model: str, corpus: list[str], entity: str, count: int
) -> list[str]:
    context = select_context(corpus, entity)
    user_msg = (
        f"Patrones de fraude reales detectados en España:\n\n{context}\n\n"
        f"Genera exactamente {count} SMS de smishing distintos que suplanten a: {entity}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.9,
        max_tokens=1024,
    )
    raw = response.choices[0].message.content.strip()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    result = []
    for l in lines:
        if not (20 <= len(l) <= 200):
            continue
        if "i'm sorry" in l.lower() or "i cannot" in l.lower() or "i can't" in l.lower():
            continue
        if "http" not in l:
            continue
        result.append(l)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera smishing con ChromaDB + Groq")
    parser.add_argument("--chroma", type=Path, required=True, help="Ruta al chroma_db")
    parser.add_argument("--out", type=Path, required=True, help="CSV de salida")
    parser.add_argument("--per-entity", type=int, default=10, help="SMS por entidad")
    parser.add_argument("--model", default="llama3-70b-8192", help="Modelo Groq")
    parser.add_argument("--entities", default="", help="Entidades a generar (separadas por coma); vacío = todas")
    parser.add_argument("--append", action="store_true", help="Añadir al CSV sin sobreescribir")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        sys.exit("Falta GROQ_API_KEY en el entorno.")
    if not args.chroma.exists():
        sys.exit(f"ChromaDB no encontrado en {args.chroma}")

    try:
        from groq import Groq
    except ImportError:
        sys.exit("Instala groq: pip install groq>=0.9")

    print(f"Cargando corpus de {args.chroma}...")
    corpus = load_corpus(args.chroma)
    print(f"  {len(corpus)} fragmentos cargados.")

    groq_client = Groq(api_key=api_key)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    entities = (
        [e.strip() for e in args.entities.split(",") if e.strip()]
        if args.entities
        else ENTITIES
    )
    mode = "a" if args.append else "w"
    with args.out.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "source"])
        if not args.append:
            writer.writeheader()
        for entity in entities:
            print(f"Generando {args.per_entity} SMS para: {entity}...")
            try:
                messages = generate_for_entity(
                    groq_client, args.model, corpus, entity, args.per_entity
                )
                for msg in messages:
                    writer.writerow({"text": msg, "label": "fraud", "source": "smishing-groq"})
                total += len(messages)
                print(f"  {len(messages)} SMS generados.")
                # ES: Pausa para respetar el rate limit de Groq free tier.
                time.sleep(2)
            except Exception as e:
                print(f"  Error con {entity}: {e}", file=sys.stderr)

    print(f"\nTotal: {total} SMS guardados en {args.out}")
    print("Revisa una muestra manualmente antes de añadir al entrenamiento.")


if __name__ == "__main__":
    main()
