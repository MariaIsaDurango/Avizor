"""Tests para los validadores _is_valid de los scripts de generación (#146)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import generate_legit
import generate_smishing


# ---------------------------------------------------------------------------
# generate_legit._is_valid
# ---------------------------------------------------------------------------

VALID_LEGIT = "Tu factura de octubre está disponible en https://iberdrola.es/facturas/oct24"
VALID_LEGIT_SHORT = "Pago recibido. Consulta tu extracto en https://bbva.es/app/extracto/nov24"


def test_legit_accepts_valid():
    assert generate_legit._is_valid(VALID_LEGIT)


def test_legit_rejects_cjk():
    assert not generate_legit._is_valid(
        "Tu factura https://correos.es/abc se関联ó correctamente"
    )


def test_legit_rejects_url_only():
    assert not generate_legit._is_valid("https://correos.es/seguimiento/AB1234")


def test_legit_rejects_too_short():
    assert not generate_legit._is_valid("Ok https://x.es")


def test_legit_rejects_too_long():
    assert not generate_legit._is_valid("a" * 140 + " https://correos.es/x")


def test_legit_rejects_shortener():
    assert not generate_legit._is_valid(
        "Tu paquete ha llegado. Rastréalo aquí: https://bit.ly/3xABCD"
    )


def test_legit_rejects_scam_domain():
    assert not generate_legit._is_valid(
        "Factura disponible en https://iberdrola-pagos.com/oct24"
    )


def test_legit_rejects_scam_word():
    assert not generate_legit._is_valid(
        "URGENTE: Tu cuenta ha sido bloqueada. Accede: https://santander.es/unlock"
    )


def test_legit_rejects_no_url():
    assert not generate_legit._is_valid(
        "Tu paquete está listo para recoger en la oficina más cercana."
    )


def test_legit_domain_check_accepts_correct():
    assert generate_legit._is_valid(
        "Movimiento en tu cuenta. Revísalo en https://santander.es/alertas/mov123",
        allowed_domains=["santander.es"],
    )


def test_legit_domain_check_rejects_wrong():
    assert not generate_legit._is_valid(
        "Movimiento en tu cuenta. Revísalo en https://google.com/fake",
        allowed_domains=["santander.es"],
    )


def test_legit_domain_check_skipped_when_none():
    assert generate_legit._is_valid(VALID_LEGIT, allowed_domains=None)


# ---------------------------------------------------------------------------
# generate_smishing._is_valid  (require_url=False → no-link style)
# ---------------------------------------------------------------------------

VALID_NO_LINK = "Has ganado un sorteo de 500€. Responde SI para reclamarlo. Válido 24h."


def test_nolink_accepts_valid():
    assert generate_smishing._is_valid(VALID_NO_LINK, require_url=False)


def test_nolink_rejects_https():
    assert not generate_smishing._is_valid(
        "Has ganado un premio. Reclámalos en https://premio.com/claim",
        require_url=False,
    )


def test_nolink_rejects_www():
    assert not generate_smishing._is_valid(
        "Has ganado un premio. Visita www.premio-gratis.es para reclamarlo.",
        require_url=False,
    )


def test_nolink_rejects_bare_domain():
    assert not generate_smishing._is_valid(
        "Has ganado 500€. Entra en premio-web.com para reclamarlos.",
        require_url=False,
    )


def test_nolink_rejects_cjk():
    assert not generate_smishing._is_valid(
        "Has ganado un sorteo de 500€. 关联 Responde SI.",
        require_url=False,
    )


def test_link_style_accepts_valid():
    assert generate_smishing._is_valid(
        "Su paquete está retenido. Pague la tasa: https://correos-aduanas.com/pago/XZ88",
        require_url=True,
    )


def test_link_style_rejects_official_domain():
    assert not generate_smishing._is_valid(
        "Su paquete está retenido. Acceda en https://sede.seg-social.gob.es/pago",
        require_url=True,
    )
