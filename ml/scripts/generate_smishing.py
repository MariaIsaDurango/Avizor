"""Genera SMS de smishing sintéticos en español usando ChromaDB + Groq (#146).

ES: Lee el corpus de avisos oficiales (INCIBE, OSI, Banco de España) de ChromaDB
    y lo usa como contexto para que Groq genere ejemplos de smishing realistas
    en español de España. La salida es un CSV con columnas text, label, source.

    Dos estilos (--style):
      link     (defecto) SMS con enlace falso suplantando entidad conocida.
      no-link  SMS corto sin enlace: premio, herencia, verificación de cuenta.

EN: Reads the official-notices corpus (INCIBE, OSI, Banco de España) from
    ChromaDB and uses it as context for Groq to generate realistic Spanish
    smishing examples. Output CSV has columns text, label, source.

Uso / Usage:
    GROQ_API_KEY=sk-... python scripts/generate_smishing.py \
        --chroma ../rag/chroma_db \
        --out data/raw/smishing_groq.csv \
        [--per-entity 25] [--model qwen/qwen3.8-27b] [--style link|no-link]
"""

import argparse
import csv
import os
import re
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

ENTITIES_NO_LINK = [
    "premio o sorteo ganador (lotería, supermercado, operadora)",
    "herencia o transferencia bancaria inesperada de desconocido",
    "verificación urgente de cuenta bancaria o tarjeta bloqueada",
    "oferta de trabajo desde casa con sueldo muy alto",
    "paquete retenido (instrucción de llamar o responder, sin enlace)",
    "alerta de acceso no autorizado a cuenta o dispositivo",
    "subsidio o ayuda gubernamental pendiente de cobro",
    "reembolso fiscal o devolución de Hacienda pendiente",
    "código de verificación enviado sin haberlo solicitado",
    "mensaje de un familiar en apuros pidiendo dinero urgente",
]

SYSTEM = (
    "Eres un generador de datos de entrenamiento para un detector de fraude por SMS. "
    "Tu tarea es crear ejemplos realistas de smishing en español de España. "
    "Reglas estrictas:\n"
    "- Menos de 160 caracteres por SMS.\n"
    "- Suplanta siempre la entidad indicada.\n"
    "- Tono urgente: amenaza, multa pendiente, paquete retenido, cuenta bloqueada, etc.\n"
    "- Incluye un enlace claramente inventado (ej: https://correos-entrega.com/seguimiento).\n"
    "- NUNCA uses acortadores reales (amzn.to, bit.ly, t.co, goo.gl, etc.).\n"
    "- NUNCA uses dominios oficiales del gobierno (.gov.es, .gob.es, .seg-social.es, etc.).\n"
    "- Usa dominios inventados con guiones (ej: amazon-es-envio.com, correos-seguimiento.net).\n"
    "- Español natural de España (tuteo o ustedeo, vocabulario peninsular).\n"
    "- Sin saludos de email ('Estimado cliente', 'Buenos días', etc.).\n"
    "- Cada SMS debe tener un gancho distinto (multa, paquete, cuenta, verificación, premio…).\n"
    "- No empieces ninguna línea con número seguido de punto o paréntesis.\n"
    "- Devuelve SOLO los SMS, uno por línea, sin numeración, sin comillas, sin explicaciones."
)

SYSTEM_NO_LINK = (
    "Eres un generador de datos de entrenamiento para un detector de fraude por SMS. "
    "Tu tarea es crear ejemplos realistas de smishing SIN ENLACE en español de España. "
    "Reglas estrictas:\n"
    "- Menos de 160 caracteres por SMS.\n"
    "- Tono urgente: premio, herencia, cuenta bloqueada, verificación, familiar en apuros.\n"
    "- NO incluyas ningún enlace (ni http://, ni www., ni acortadores).\n"
    "- Puedes incluir un número de teléfono inventado (ej: 900 123 456) o pedir que "
    "respondan al SMS con una palabra clave (ej: 'Responde SI para reclamar').\n"
    "- Español natural de España (tuteo o ustedeo, vocabulario peninsular).\n"
    "- Sin saludos de email ('Estimado cliente', 'Buenos días', etc.).\n"
    "- Cada SMS debe tener un gancho distinto.\n"
    "- No empieces ninguna línea con número seguido de punto o paréntesis.\n"
    "- Devuelve SOLO los SMS, uno por línea, sin numeración, sin comillas, sin explicaciones."
)

_REAL_SHORTENERS = re.compile(r"amzn\.to|bit\.ly|t\.co|goo\.gl|ow\.ly|tinyurl\.com")
_OFFICIAL_DOMAINS = re.compile(r"\.(gov|gob)\.es|seg-social\.es")


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


def _is_valid(line: str, require_url: bool = True) -> bool:
    if not (20 <= len(line) <= 160):
        return False
    lower = line.lower()
    if "i'm sorry" in lower or "i cannot" in lower or "i can't" in lower:
        return False
    if require_url and not re.search(r"https?://", line, re.IGNORECASE):
        return False
    if not require_url and re.search(r"https?://", line, re.IGNORECASE):
        return False
    if _REAL_SHORTENERS.search(line):
        return False
    if _OFFICIAL_DOMAINS.search(line):
        return False
    return True


def generate_for_entity(
    client, model: str, corpus: list[str], entity: str, count: int, style: str
) -> list[str]:
    system_prompt = SYSTEM_NO_LINK if style == "no-link" else SYSTEM
    require_url = style != "no-link"
    if style == "no-link":
        user_msg = (
            f"Genera exactamente {count} SMS de smishing distintos sin enlace "
            f"con el gancho: {entity}"
        )
    else:
        context = select_context(corpus, entity)
        user_msg = (
            f"Patrones de fraude reales detectados en España:\n\n{context}\n\n"
            f"Genera exactamente {count} SMS de smishing distintos que suplanten a: {entity}"
        )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.9,
        max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return [line for line in lines if _is_valid(line, require_url=require_url)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera smishing con ChromaDB + Groq")
    parser.add_argument("--chroma", type=Path, default=None, help="Ruta al chroma_db (requerido para --style link)")
    parser.add_argument("--out", type=Path, required=True, help="CSV de salida")
    parser.add_argument("--per-entity", type=int, default=25, help="SMS por entidad")
    parser.add_argument("--model", default="qwen/qwen3.8-27b", help="Modelo Groq")
    parser.add_argument("--style", choices=["link", "no-link"], default="link", help="Estilo de smishing")
    parser.add_argument("--entities", default="", help="Entidades (separadas por coma); vacío = todas")
    parser.add_argument("--append", action="store_true", help="Añadir al CSV sin sobreescribir")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        sys.exit("Falta GROQ_API_KEY en el entorno.")

    corpus = []
    if args.style == "link":
        if not args.chroma:
            sys.exit("--chroma es obligatorio para --style link.")
        if not args.chroma.exists():
            sys.exit(f"ChromaDB no encontrado en {args.chroma}")
        try:
            from groq import Groq
        except ImportError:
            sys.exit("Instala groq: pip install groq>=0.9")
        print(f"Cargando corpus de {args.chroma}...")
        corpus = load_corpus(args.chroma)
        print(f"  {len(corpus)} fragmentos cargados.")
    else:
        try:
            from groq import Groq
        except ImportError:
            sys.exit("Instala groq: pip install groq>=0.9")

    groq_client = Groq(api_key=api_key)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    entity_list = ENTITIES_NO_LINK if args.style == "no-link" else ENTITIES
    if args.entities:
        entity_list = [e.strip() for e in args.entities.split(",") if e.strip()]

    source_label = "smishing-no-link-groq" if args.style == "no-link" else "smishing-groq"
    mode = "a" if args.append else "w"
    with args.out.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "source"])
        if not args.append:
            writer.writeheader()
        for entity in entity_list:
            print(f"Generando {args.per_entity} SMS para: {entity}...")
            try:
                messages = generate_for_entity(
                    groq_client, args.model, corpus, entity, args.per_entity, args.style
                )
                for msg in messages:
                    writer.writerow({"text": msg, "label": "fraud", "source": source_label})
                total += len(messages)
                print(f"  {len(messages)} SMS generados.")
                time.sleep(2)
            except Exception as e:
                print(f"  Error con {entity}: {e}", file=sys.stderr)

    print(f"\nTotal: {total} SMS guardados en {args.out}")
    print("Revisa una muestra manualmente antes de añadir al entrenamiento.")


if __name__ == "__main__":
    main()
