# ADR 0007: OCR de imágenes en el servidor con Tesseract

**Fecha:** 2026-11-26
**Estado:** Aceptado (MVP)
**Autora:** Isa · acordado con Majo (#165, #192)

---

## Contexto

El Sénior puede reenviar capturas de pantalla. Hasta ahora el backend solo leía
el texto de los PDF (#164). Una imagen sin `local_preprocessing` no aportaba
texto y el análisis salía GREEN ("seguro").

Opciones valoradas:

| Opción | Problema |
|---|---|
| OCR en el móvil (ML Kit) | Aumenta el tamaño de la APK y es bastante trabajo en el móvil. |
| Modelo de visión de Groq | Envía la imagen sin anonimizar a un tercero (rompe el contrato). `llama-3.2-11b-vision-preview` ya está retirado. |
| **Tesseract en el servidor** | La imagen Docker crece unos MB. Calidad suficiente para capturas. |

---

## Decisión

1. **Tesseract local** (`tesseract-ocr` + `tesseract-ocr-spa`) en la imagen
   Docker y en CI. Sin dependencias pip.
2. **Nada a disco:** la imagen entra por stdin y el texto sale por stdout. No se
   usa `pytesseract`, que escribe archivos temporales.
3. **Mismo camino que el PDF:** texto extraído → `anonymize()` → clasificador y
   agente. Se valida la firma real (JPEG, PNG, WebP, HEIC); si no, 422.
4. **Límites:** 8 s por imagen y 5000 caracteres.
5. **Sin texto legible no es "seguro":** si el envío no trae texto propio y no
   se pudo leer ningún adjunto (imagen sin texto, HEIC, PDF escaneado), el
   veredicto es AMBER, plantilla `UNSURE_CALL_FAMILY`, confianza 0.3, sin
   alerta al Tutor y sin llamar al agente.
6. El móvil no cambia: sigue enviando `type: image` sin `local_preprocessing`.

---

## Consecuencias

- HEIC no se lee (Leptonica no lo soporta): sale AMBER "no pudimos leer".
- Los nombres de personas se tapan desde #193 (ADR 0009).
- Los datos médicos no los cubre ningún NER: limitación documentada.
