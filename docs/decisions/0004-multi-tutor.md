# ADR 0004: Varios Tutores por Sénior y aprobación de desbloqueos

**Fecha:** 2026-11-19
**Estado:** Aceptado (provisional para el MVP)
**Autora:** Isa

---

## Contexto

El planteamiento deja abierto si un Sénior puede tener más de un Tutor (por
ejemplo, dos hijos) y, en ese caso, quién aprueba las solicitudes de
desbloqueo (`POST /api/v1/unlocks`) cuando el Sénior quiere continuar con una
acción bloqueada.

Hay que decidirlo porque afecta a:

- el modelo de datos (`pairings`),
- a quién se envían las alertas y los avisos push,
- qué pasa al desvincular (`DELETE /api/v1/senior`, #117),
- quién puede resolver un desbloqueo (`PATCH /api/v1/unlocks/{id}`).

---

## Alternativas consideradas

### A. Un solo Tutor por Sénior
- Lo más simple de explicar y de probar.
- Si el Tutor no responde, nadie más puede aprobar un desbloqueo.
- Habría que cambiar el modelo más adelante para admitir varios.

### B. Varios Tutores con los mismos permisos (el primero que responde decide)
- Cualquier Tutor vinculado recibe las alertas y puede aprobar o rechazar.
- Más probable que alguien responda a tiempo.
- Riesgo: dos Tutores responden a la vez con decisiones distintas.

### C. Varios Tutores con un Tutor principal
- Solo el principal aprueba desbloqueos; los demás solo reciben alertas.
- Más control, pero añade roles, transferencia del rol y más pantallas.
- Demasiado para el alcance del MVP.

---

## Decisión

**Modelo preparado para varios Tutores (B), pero en el MVP cada Sénior tiene un solo Tutor.**

Cómo funciona hoy en el backend:

1. **Modelo de datos:** la tabla `pairings` relaciona Tutor y Sénior, así que
   admite N Tutores por Sénior sin cambios de esquema.
2. **Vinculación en el MVP:** canjear un código (`POST /pairings/redeem`) crea
   siempre un Sénior nuevo. Un segundo Tutor no puede unirse a un Sénior ya
   vinculado, así que en la práctica hay un Tutor por Sénior.
3. **Alertas:** se crea una alerta para cada Tutor con vinculación activa
   (`services/analysis.py`).
4. **Desbloqueos:** cualquier Tutor con vinculación activa puede resolverlos.
   La fila se bloquea con `SELECT ... FOR UPDATE`: el primero que responde
   decide y el segundo recibe `409` ("Esta solicitud ya no está pendiente").
5. **Desvincular:** solo desactiva la vinculación del Tutor que lo pide. Si el
   Sénior se queda sin ningún Tutor activo, se le da de baja (`deleted_at`) y
   su token deja de valer (#117).
6. **`GET /api/v1/senior`:** devuelve la vinculación activa más reciente del
   Tutor.

---

## Consecuencias

- No hace falta migración para admitir varios Tutores más adelante.
- Falta el flujo para que un segundo Tutor se una a un Sénior existente: un
  código de invitación emitido por un Tutor ya vinculado, que añada una fila
  en `pairings` sin crear otro Sénior. Queda fuera del MVP.
- Con varios Tutores, el aviso de cierre de sesión del Sénior (#127) y las
  alertas ya llegan a todos.
- Un Tutor con varios Sénior solo ve uno en `GET /senior`. Si se admite,
  habrá que cambiar ese endpoint a una lista (cambio MINOR del contrato).
- Consentimiento (RGPD): las alertas dicen al Tutor qué tipo de amenaza
  recibió el Sénior, por qué canal y cuándo. Son datos personales del Sénior.
  Hoy el consentimiento (`POST /consents`, tabla `consents`) se guarda por
  Sénior y canal, pero no dice para qué Tutor es. Si se añadiera un segundo
  Tutor, quedaría cubierto por el consentimiento existente sin que el Sénior
  lo sepa, y sería otra persona recibiendo sus datos. Por eso, antes de
  activar varios Tutores, el consentimiento tiene que indicar a qué Tutor
  autoriza (o pedirse de nuevo para cada uno, al Sénior o a su tutor legal), y
  el Sénior debe poder ver quién recibe sus alertas y retirar a cualquiera.

---

## Pendiente de validar

- **José (privacidad):** el consentimiento por cada Tutor descrito arriba,
  antes de activar el flujo de varios Tutores.
