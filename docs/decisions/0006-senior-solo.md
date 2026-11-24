# ADR 0006: Sénior sin Tutor (`senior_solo`)

**Fecha:** 2026-11-24
**Estado:** Aceptado (MVP)
**Autora:** Isa · acordado con Majo (#174, #175)

---

## Contexto

El planteamiento define dos perfiles: el Sénior protegido y el Tutor que lo
configura y recibe las alertas. Hay personas mayores sin un familiar que pueda
hacer de Tutor. Para ellas se pide un perfil híbrido: la protección del Sénior
más parte de lo que ve el Tutor (su historial).

El rol `senior_solo` no está en el Contrato v1.0.0. Es un añadido MINOR.

---

## Decisión

1. **Rol nuevo `senior_solo`** en `user_role` (migración 0009).
2. **Registro propio:** `POST /api/v1/auth/register` con `role: "senior_solo"` y
   `device: {platform, app_version}`. Se crean el usuario **y su dispositivo**.
   Verifica el email con código y recupera la contraseña igual que el Tutor.
3. **Token con dispositivo:** como el Sénior vinculado, el token lleva
   `sub = device_id`. Así reutiliza la vía rápida, el análisis manual, los
   consentimientos, la retención y las estadísticas sin cambios. Al tener
   contraseña, su token también usa `token_version` (cambiar la contraseña
   cierra sus sesiones).
4. **`device_id` opcional** en `POST /api/v1/analyses` (JSON y multipart) solo
   para `senior_solo`: si falta, se usa el de su token. El Sénior vinculado
   debe seguir enviándolo. El login y `GET /auth/me` devuelven `device_id`.
5. **Consentimiento propio** (`type: "self"`), como el Sénior vinculado.
6. **Sin alertas:** sin Tutor no hay a quién avisar. Un rojo muestra la pantalla
   de bloqueo y queda en su historial (#175). No se crean filas en `alerts`.
7. **Sin auto-desbloqueo en el MVP:** `POST /api/v1/unlocks` responde 403. Un
   estafador que le presione por teléfono podría pedirle que se desbloquee. La
   plantilla de bloqueo le sugiere llamar a alguien de confianza.
8. **Vincular un Tutor más adelante:** fuera del MVP. El diseño no lo impide.

---

## Alternativas consideradas

- **Análisis sin dispositivo (`device_id` nulo en `analyses`).** Descartada:
  `device_id` es obligatorio en la tabla y de él dependen consentimientos,
  retención, estadísticas y verdictos. Habría que tocar todo el backend.
- **Usar el rol `senior` sin vinculación.** Descartada: el Sénior no tiene
  email ni contraseña (entra con código de vinculación) y la app necesita
  distinguir el perfil híbrido.

---

## Consecuencias

- Contrato: rol nuevo, campos `device` (registro) y `device_id` (login, `/me`),
  y `device_id` opcional en análisis para este rol.
- Pendiente para José: revisar el punto 7 y el consentimiento sin Tutor (RGPD).
- Pendiente (#175): `GET /api/v1/my-analyses` para su historial.
- Fuera de alcance: cambiar contraseña y editar perfil desde la app (hoy solo
  Tutor), perfil de accesibilidad del `senior_solo`.
