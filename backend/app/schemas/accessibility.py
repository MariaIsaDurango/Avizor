"""Perfil de accesibilidad del Sénior.
Senior accessibility profile.

ES: La app del Sénior usa estos indicadores para adaptar su interfaz
    (contraste, tamaño de letra, lector de pantalla, avisos visuales).
    Son datos de salud (art. 9 RGPD): solo cuatro casillas, sin texto libre,
    y se rechazan campos desconocidos para no guardar nada que no se pidió.
EN: The senior app uses these flags to adapt its interface (contrast, font
    size, screen reader, visual alerts). They are health data (GDPR art. 9):
    only four flags, no free text, and unknown fields are rejected so nothing
    that was not requested is stored.
"""

from pydantic import BaseModel, ConfigDict


class AccessibilityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color_blindness: bool = False
    low_vision: bool = False
    blindness: bool = False
    hearing_impairment: bool = False
