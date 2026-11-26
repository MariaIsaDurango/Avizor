# ADR 0009: Nombres de personas en el texto que extrae el servidor

**Fecha:** 2026-11-26
**Estado:** Aceptado (MVP)
**Autora:** Isa (#193)

---

## Contexto

El texto de PDF e imágenes no pasa por el móvil. El servidor lo anonimiza con
`regex-v0` (IBAN, tarjeta, DNI/NIE, email, teléfono, dirección), pero los
nombres de personas no se tapaban.

Pruebas con mensajes de estafa inventados:

| Modelo spaCy | RAM extra | Resultado |
|---|---|---|
| `es_core_news_sm` | ~160 MB | Tapa por error "Mamá", "WhatsApp", "Receta" y marca "Verifique" como lugar. |
| `es_core_news_md` | ~350 MB | Acierta en esos casos. No ve nombres en mayúsculas ("PEDRO GOMEZ"). |

---

## Decisión

1. **spaCy `es_core_news_md`, local.** Solo personas (`PER`) → `[NAME]`.
   Lugares y organizaciones se quedan: el banco o "Correos" son señal de estafa.
2. **Solo el nombre:** se quitan saludos, tratamientos y siglas del tramo
   ("Hola Carmen" → "Hola [NAME]"; "Carmen Ruiz DNI" → "[NAME] DNI").
3. **Segunda capa sin modelo:** tras Sr./Sra./Don/Doña/Dr./Estimado/a/Titular/
   Paciente/Nombre va un nombre aunque el NER no lo vea. Excepción: palabras de
   familia ("Querida Mamá").
4. **Orden:** primero `regex-v0` (igual que el móvil), después nombres.
5. **Carga perezosa:** el modelo se carga con el primer archivo; no gasta RAM si
   nadie envía archivos. `AVIZOR_NER_MODEL` elige el modelo; vacío lo desactiva.
6. El texto del móvil no cambia (sigue `regex-v0` en el dispositivo).

---

## Consecuencias

- Railway: el plan de prueba (1 GB) llega a la entrega (10/12/2026). Con el plan
  Free (0,5 GB) hay que usar `sm` o desactivarlo.
- La imagen Docker crece unos 240 MB.
- Los datos médicos (diagnósticos, fármacos) siguen sin taparse: limitación.
