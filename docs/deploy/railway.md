# Despliegue del backend en Railway (#122)

El backend (API + portal web) se despliega como un contenedor Docker con
`backend/Dockerfile`. La base de datos es el PostgreSQL de Railway.

No usamos `railway.json`: Railway lo ha marcado como obsoleto (Config as Code)
y los servicios nuevos no pueden usarlo. Todo se configura con variables y
desde el panel.

## Qué hace el contenedor al arrancar

`backend/docker-entrypoint.sh`:

1. `alembic upgrade head`: aplica las migraciones pendientes. Si falla, el
   contenedor no arranca.
2. `uvicorn app.main:app` en el puerto `PORT` que da Railway, con un solo
   proceso (la purga de retención corre dentro de la app y no debe duplicarse).

La imagen se construye desde la raíz del repo porque el backend importa
`rag/src/reputation` (#42). Solo copia lo necesario para ejecutar: sin tests,
sin `mobile/` y sin `ml/`.

## Pasos en Railway

1. **New Project → Deploy from GitHub repo** → `MariaIsaDurango/Avizor`.
   - Rama: `main` (o `dev` para pruebas).
   - Root Directory: vacío (la raíz del repo).
2. **+ New → Database → PostgreSQL** en el mismo proyecto.
3. En el servicio del backend, pestaña **Variables**:

   | Variable | Valor |
   |---|---|
   | `RAILWAY_DOCKERFILE_PATH` | `backend/Dockerfile` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia al servicio de Postgres) |
   | `JWT_SECRET` | 64 caracteres aleatorios: `openssl rand -hex 32` |
   | `PHONE_HMAC_KEY` | otros 64 caracteres distintos: `openssl rand -hex 32` |
   | `APP_ENV` | `production` |
   | `FRONTEND_URL` | `https://<dominio-de-railway>` (paso 4) |
   | `MAIL_PROVIDER` | `smtp` |
   | `MAIL_USERNAME` | `avizorapp1.0@gmail.com` |
   | `MAIL_PASSWORD` | contraseña de aplicación de Gmail |
   | `MAIL_FROM` | `avizorapp1.0@gmail.com` |
   | `PUSH_PROVIDER` | `expo` (cuando la app tenga push real; si no, `log`) |

   `DATABASE_URL` puede llegar como `postgresql://...`: el backend lo convierte
   solo a `postgresql+psycopg://...`.

   No hace falta `CHROMADB_*`: el backend todavía no usa ChromaDB (el RAG se
   integrará más adelante).

4. **Settings → Networking → Generate Domain**. Copia la URL y ponla en
   `FRONTEND_URL`.
5. **Settings → Deploy → Healthcheck Path**: `/api/v1/health`.
6. Despliega y comprueba:

   ```
   https://<dominio>/api/v1/health
   → {"status":"ok","contract_version":"1.0.0"}
   ```

## Después del despliegue

- **App móvil**: en `mobile/.env.local`,
  `EXPO_PUBLIC_API_URL=https://<dominio>`. Para builds con EAS, la misma
  variable en `eas.json` o en el panel de EAS.
- **Portal web**: se sirve desde el mismo dominio, no hay que cambiar nada.
- Los secretos solo van en las variables de Railway, nunca en el repo.

## Probar la imagen en local (opcional, con Docker Desktop)

```
docker build -f backend/Dockerfile -t avizor-backend .
docker run --rm -p 8000:8000 --env-file .env avizor-backend
```

Con la base de datos de `docker-compose.yml`, en el `.env` usa
`host.docker.internal` en lugar de `localhost` en `DATABASE_URL`.
