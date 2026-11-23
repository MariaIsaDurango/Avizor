# ADR 0005: Umbral para publicar indicadores en el ranking

**Fecha:** 2026-11-19
**Estado:** Aceptado (provisional para el MVP)
**Autora:** Isa

---

## Contexto

El portal web muestra un ranking público de indicadores maliciosos (dominios
y teléfonos) en `GET /api/v1/stats/indicators`. Publicar un indicador con
pocos reportes tiene dos riesgos:

- **Falsos positivos:** un número o dominio legítimo marcado por error
  aparecería como atacante.
- **Privacidad:** un indicador visto por una sola persona puede revelar algo
  de esa persona (por ejemplo, quién le escribe).

El contrato pide no publicar indicadores que no alcancen un umbral. La
propuesta inicial era 5 reportes o más.

---

## Alternativas consideradas

### A. Publicar todo lo detectado
- Más datos en el ranking.
- Inaceptable: publica falsos positivos y datos de una sola persona.

### B. Umbral fijo de reportes (≥5)
- Simple, se aplica en una vista de la base de datos.
- Limitación: hoy `report_count` cuenta detecciones, no personas distintas.
  Cinco mensajes al mismo Sénior suman 5.

### C. Umbral por Sénior distintos (k-anonimato, ≥5 personas)
- Protege mejor: hace falta que 5 personas distintas lo hayan recibido.
- Requiere guardar qué Sénior reportó cada indicador (tabla nueva y más
  datos personales que proteger y borrar).

---

## Decisión

**Umbral fijo de 5 reportes (B) para el MVP.**

Cómo está aplicado:

1. La vista `v_indicator_ranking` (migración 0001) solo devuelve indicadores
   con `report_count >= 5`, ordenados de más a menos reportes, y el endpoint
   limita a 100 filas.
2. Los teléfonos se publican solo en formato enmascarado (`public_value`); el
   valor real se guarda como HMAC (`value_hash`) y nunca sale del backend.
3. El mismo umbral de 5 marca un remitente como RED en la vía rápida
   (`REPORTS_RED = 5` en `services/detection/decision.py`), y 1 reporte lo
   marca como AMBER.
4. Los indicadores sin reportes en 12 meses se borran en la purga de
   retención (si no tienen casos asociados).

---

## Consecuencias

- El ranking puede tardar en llenarse durante las pruebas: hacen falta 5
  detecciones del mismo indicador.
- Riesgo aceptado para el MVP: varias detecciones en el mismo Sénior cuentan
  como reportes distintos. Mejora futura (opción C): contar Sénior distintos
  antes de publicar, sin guardar quién es cada uno (por ejemplo, un HMAC del
  `senior_id` por indicador).
- Cambiar el umbral solo requiere una migración que recree la vista y ajustar
  `REPORTS_RED` si se quiere mantener igual en la detección.

---

## Pendiente de validar

- **José (privacidad):** que 5 reportes basten para publicar un indicador sin
  exponer a una persona concreta, mientras no se cuenten Sénior distintos.
- **María (datos de reputación):** que el umbral de 5 encaje con los
  indicadores que llegan de las fuentes oficiales y las APIs de reputación.
