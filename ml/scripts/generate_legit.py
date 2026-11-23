"""Genera SMS legítimos con enlace en español para equilibrar el dataset (#146).

ES: Crea ejemplos de SMS auténticos (confirmaciones, avisos, citas) que incluyen
    un enlace, para contrarrestar el sesgo "enlace = estafa" en el clasificador.
    La salida es un CSV con columnas text, label, source compatible con load_spamspa().

EN: Creates authentic SMS examples (confirmations, notices, appointments) that
    include a link, to counteract the "link = scam" bias in the classifier.
    Output CSV has columns text, label, source compatible with load_spamspa().

Uso / Usage:
    GROQ_API_KEY=sk-... python scripts/generate_legit.py \\
        --out data/raw/legit_links_groq.csv \\
        [--per-entity 25] [--model gemma2-9b-it]
"""

import argparse
import csv
import os
import re
import sys
import time

ENTITIES = [
    ("Correos de España", "aviso de paquete listo para recoger o entregado en buzón"),
    ("Banco Santander", "confirmación de transferencia o alerta de movimiento en cuenta"),
    ("BBVA", "confirmación de pago o extracto mensual disponible"),
    ("CaixaBank", "factura o notificación de operación disponible en la app"),
    ("Agencia Tributaria (AEAT)", "declaración de la renta disponible o notificación en sede electrónica"),
    ("Dirección General de Tráfico (DGT)", "cita para renovar permiso de conducir o notificación de trámite"),
    ("Seguridad Social", "cita médica confirmada o notificación de prestación"),
    ("Iberdrola", "factura del mes disponible o aviso de lectura del contador"),
    ("Amazon España", "pedido enviado o entregado, enlace de seguimiento"),
    ("Centro de salud", "recordatorio de cita médica con enlace para confirmar o cancelar"),
    ("Farmacia online Lozano", "pedido enviado con número de seguimiento y enlace de rastreo"),
    ("Clínica dental San Pablo", "recordatorio de cita con enlace para confirmar o cancelar"),
    ("Gestoría Marín & Asociados", "documentación lista para descargar en el área cliente"),
    ("Academia online EduPro", "nuevo curso o material disponible en la plataforma"),
    ("Tienda de ropa Modalia", "pedido enviado o listo para recoger, enlace de seguimiento"),
]

SYSTEM = (
    "Eres un generador de datos de entrenamiento para un detector de fraude por SMS. "
    "Tu tarea es crear ejemplos realistas de SMS LEGÍTIMOS en español de España, "
    "es decir, mensajes auténticos de empresas o instituciones que incluyen un enlace. "
    "Reglas estrictas:\n"
    "- Menos de 160 caracteres por SMS.\n"
    "- Tono informativo y neutro, NUNCA urgente ni amenazante.\n"
    "- Incluye un enlace de aspecto oficial con dominio real de la entidad "
    "(ej: https://correos.es/seguimiento/XY1234, https://www.bbva.es/app/factura/oct24, "
    "https://sede.agenciatributaria.gob.es/renta).\n"
    "- Usa dominios reales o de aspecto oficial; NUNCA dominios inventados con guiones "
    "(correos-seguimiento.com, bbva-avisos.net, etc.).\n"
    "- NUNCA uses acortadores (bit.ly, t.co, goo.gl, amzn.to, etc.).\n"
    "- Español natural de España (tuteo o ustedeo, vocabulario peninsular).\n"
    "- Sin saludos de email ('Estimado cliente', 'Buenos días', etc.).\n"
    "- Tipos de mensaje: paquete entregado, factura disponible, cita confirmada, "
    "pago realizado, código de verificación, trámite listo, lectura contador.\n"
    "- Cada SMS debe tener un motivo distinto dentro del tipo de la entidad.\n"
    "- No empieces ninguna línea con número seguido de punto o paréntesis.\n"
    "- Devuelve SOLO los SMS, uno por línea, sin numeración, sin comillas, sin explicaciones."
)

_SHORTENERS = re.compile(r"bit\.ly|t\.co|goo\.gl|amzn\.to|ow\.ly|tinyurl\.com")
_SCAM_DOMAINS = re.compile(r"https?://[^\s]*[-][^\s]*\.(com|net|info|xyz|top|click)", re.I)
_SCAM_WORDS = re.compile(
    r"\b(urgente|inmediatamente|bloqueada|suspendida|multado|retenido|vence hoy|"
    r"último aviso|impago|deuda|cancelar.{0,15}cuenta)\b",
    re.I,
)


def _is_valid(line: str) -> bool:
    if not (20 <= len(line) <= 200):
        return False
    lower = line.lower()
    if "i'm sorry" in lower or "i cannot" in lower or "i can't" in lower:
        return False
    if not re.search(r"https?://", line, re.IGNORECASE):
        return False
    if _SHORTENERS.search(line):
        return False
    if _SCAM_DOMAINS.search(line):
        return False
    if _SCAM_WORDS.search(line):
        return False
    return True


def generate_for_entity(client, model: str, entity: str, description: str, count: int) -> list[str]:
    user_msg = (
        f"Genera exactamente {count} SMS legítimos distintos enviados por: {entity}\n"
        f"Tipo de mensaje: {description}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
        max_tokens=800,
    )
    raw = response.choices[0].message.content.strip()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return [line for line in lines if _is_valid(line)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera SMS legítimos con enlace usando Groq")
    parser.add_argument("--out", type=str, required=True, help="CSV de salida")
    parser.add_argument("--per-entity", type=int, default=25, help="SMS por entidad")
    parser.add_argument("--model", default="qwen/qwen3.8-27b", help="Modelo Groq")
    parser.add_argument("--append", action="store_true", help="Añadir al CSV sin sobreescribir")
    parser.add_argument("--entities", default="", help="Entidades (separadas por coma); vacío = todas")
    args = parser.parse_args()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        sys.exit("Falta GROQ_API_KEY en el entorno.")

    try:
        from groq import Groq
    except ImportError:
        sys.exit("Instala groq: pip install groq>=0.9")

    from pathlib import Path

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    groq_client = Groq(api_key=api_key)
    total = 0
    mode = "a" if args.append else "w"

    with out.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label", "source"])
        if not args.append:
            writer.writeheader()
        entity_filter = {e.strip() for e in args.entities.split(",") if e.strip()}
        pairs = [(e, d) for e, d in ENTITIES if not entity_filter or e in entity_filter]
        for entity, description in pairs:
            print(f"Generando {args.per_entity} SMS para: {entity}...")
            try:
                messages = generate_for_entity(
                    groq_client, args.model, entity, description, args.per_entity
                )
                for msg in messages:
                    writer.writerow({"text": msg, "label": "ham", "source": "legit-groq"})
                total += len(messages)
                print(f"  {len(messages)} SMS generados.")
                time.sleep(2)
            except Exception as e:
                print(f"  Error con {entity}: {e}", file=sys.stderr)

    print(f"\nTotal: {total} SMS guardados en {out}")
    print("Revisa una muestra manualmente antes de añadir al entrenamiento.")


if __name__ == "__main__":
    main()
