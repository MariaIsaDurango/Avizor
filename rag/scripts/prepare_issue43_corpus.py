"""Build a reviewable academic approval manifest; never edit raw snapshots."""

import argparse
import json
from datetime import date
from pathlib import Path

from rag.src.ingestion.models import Notice

# Preliminary title-based classification for the 30 known snapshots.
# Review against the complete local articles before accepting the manifest.
LABELS = {
    "¿Te pueden engañar con una voz conocida? Así funcionan las estafas con clonación de voz": [
        "identity_theft",
        "vishing",
    ],
    "Tómate un tiempo antes de hacer click": ["phishing"],
    "Estafas por Bizum": ["bank_fraud"],
    "¡Atento a las campañas para prevenir el fraude financiero!": ["bank_fraud"],
    "Las autoridades europeas nos advierten": ["other"],
    "Estas son las nuevas medidas para combatir los fraudes por teléfono": [
        "vishing",
        "smishing",
    ],
    "Consejos para una venta segura en plataformas de segunda mano": ["other"],
    "TrickMo. Un tipo de malware que amenaza tus finanzas": ["bank_fraud", "other"],
    "¡Que no te pillen con la estafa de los likes!": ["other"],
    "¡Cuidado con las alertas falsas del Banco de España!": [
        "bank_fraud",
        "identity_theft",
    ],
    "Un falso concurso de baile permite a los ciberdelincuentes utilizar tu cuenta de WhatsApp": [
        "phishing",
        "identity_theft",
    ],
    "Los ciberdelincuentes están utilizando cuentas de WhatsApp en iPhone sin actualizar para pedir dinero a sus contactos": [
        "identity_theft"
    ],
    "Correos y SMS suplantan a la DGT para robar tus datos con falsas multas": [
        "smishing",
        "phishing",
    ],
    "Campaña de smishing suplantando a la Seguridad Social": ["smishing", "phishing"],
    "Suplantan a hoteles a través de WhatsApp y otros medios para solicitar la confirmación de reservas mediante enlaces fraudulentos": [
        "phishing",
        "identity_theft",
    ],
    "Suplantan a la Policía Nacional, a la Guardia Civil y a INCIBE a través de notificaciones falsas por consumir contenido pornográfico": [
        "identity_theft",
        "phishing",
    ],
    "Suplantan al LIDL a través de tiendas online fraudulentas": [
        "phishing",
        "identity_theft",
    ],
    "Notificaciones falsas que suplantan a la Agencia Tributaria (AEAT) y a la Dirección Electrónica Habilitada Única (DEHú)": [
        "phishing",
        "identity_theft",
    ],
    "Campaña de smishing que suplanta a empresas de paquetería con la excusa de que falta el número de casa": [
        "smishing",
        "phishing",
    ],
    "Campaña de phishing que suplanta a Iberdrola con la excusa del envío de una factura": [
        "phishing"
    ],
    "Principales fraudes en redes sociales y WhatsApp": [
        "phishing",
        "identity_theft",
        "other",
    ],
    "¿De dónde obtienen los ciberdelincuentes nuestros datos?": ["other"],
    "La estafa del familiar en apuros": ["identity_theft"],
    "No, INCIBE no ha sido víctima de un ciberataque. ¿Qué es el doxing y cómo INCIBE se ha visto afectado por esta práctica?": [
        "other"
    ],
    "Aprende a reconocer y evitar estafas con Experiencia Sénior": ["other"],
    "Servicio de Phishing Alert y su caso de uso en las suplantaciones de identidad": [
        "phishing",
        "identity_theft",
    ],
    "Black Friday y Cyber Monday. ¿Sabes cómo comprar online sin caer en estafas digitales?": [
        "other"
    ],
    "Glosario de términos básicos de ciberseguridad": ["other"],
    "Cripto robos y estafas digitales: lo que debes saber antes de invertir en criptomonedas": [
        "other"
    ],
    "Vacaciones ciberseguras: estafas en apps vacacionales": ["other"],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept-team-policy", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--labels", type=Path, help="Optional reviewed manifest draft")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose another path")
    previous = (
        json.loads(args.labels.read_text(encoding="utf-8")) if args.labels else {}
    )
    result = {}
    for path in sorted(Path("rag/data/raw").glob("*_content.json")):
        for raw in json.loads(path.read_text(encoding="utf-8")):
            url = raw["url"]
            if url in result:
                raise ValueError("Duplicate URL in raw corpus")
            labels = LABELS.get(raw["title"], ["other"])
            entry = {
                "content_hash": raw["content_hash"],
                "rag_allowed": args.accept_team_policy,
                "reference": "Decisión interna del equipo Avizor: prototipo académico no comercial; no autorización expresa del titular.",
                "threat_type": labels[0],
                "secondary_threats": labels[1:],
                "impersonated_entities": "",
                "title": raw["title"],
                "classification_status": "preliminary_title_based",
            }
            if url in previous:
                old = previous[url]
                if old["content_hash"] != raw["content_hash"]:
                    raise ValueError("Snapshot changed since review")
                for key in (
                    "threat_type",
                    "secondary_threats",
                    "impersonated_entities",
                    "classification_status",
                ):
                    if key in old:
                        entry[key] = old[key]
            # Validate source, dates, hashes and labels even in draft mode.
            Notice.from_record(
                raw,
                today=date.today(),
                synthetic=False,
                approval={**entry, "rag_allowed": True},
            )
            result[url] = entry
    if not result:
        raise ValueError("No content snapshots found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(
        f"Documents: {len(result)}; academic policy accepted: {args.accept_team_policy}"
    )


if __name__ == "__main__":
    main()
