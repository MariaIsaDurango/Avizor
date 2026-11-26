# ADR 0008: Borrar la cuenta y retirar el consentimiento sin id

**Fecha:** 2026-11-26
**Estado:** Aceptado (MVP)
**Autora:** Isa · pedido por Majo (#184, #194)

---

## Contexto

- **#184:** si el móvil no guardó `CONSENT_ID` (instalaciones antiguas), no
  puede llamar a `POST /consents/{id}/revoke` y el consentimiento sigue activo
  en la base de datos.
- **#194:** los perfiles con cuenta propia (Tutor y `senior_solo`) necesitan un
  botón "Eliminar cuenta".

Ninguno de los dos endpoints está en el Contrato v1.0.0. Son añadidos MINOR.

---

## Decisión

1. **`POST /api/v1/consents/me/revoke`** (Sénior y `senior_solo`). Retira sus
   consentimientos propios (`self`) activos y devuelve la lista de los retirados
   (vacía si no quedaba ninguno). La tutela legal la sigue retirando el Tutor.
2. **`DELETE /api/v1/auth/me`** con `{"password": "..."}`. Va junto a
   `GET` y `PATCH /auth/me`. Se pide la contraseña: un móvil desbloqueado no
   basta. Contraseña incorrecta: 400. Sénior vinculado: 403 (no tiene cuenta).
3. **Borrado físico**, no lógico: usuario, dispositivos, análisis (con adjuntos,
   texto temporal, alertas y desbloqueos), consentimientos, alertas y vínculos.
   Respuesta 204. Los tokens dejan de valer (401).
4. Se quedan los **indicadores agregados** (no identifican a nadie). Los casos
   del panel pierden el enlace al análisis y al admin asignado.
5. Si un Tutor borra su cuenta y su Sénior se queda sin Tutor, el Sénior se da
   de baja igual que al desvincular (`deleted_at`, sin `push_token`).

---

## A revisar (José)

- Al borrar también los consentimientos se pierde la prueba de que existieron
  (RGPD art. 7.1). Decisión del equipo: borrado total. Conviene confirmarlo.
