#!/bin/sh
# ES: Aplica las migraciones y arranca la API. Si la migración falla, el
#     contenedor no arranca (mejor que servir con un esquema incorrecto).
# EN: Applies migrations and starts the API. If the migration fails, the
#     container does not start (better than serving with a wrong schema).
set -e

alembic upgrade head

# ES: Un solo proceso: la purga de retención corre dentro de la app y no debe
#     duplicarse. --proxy-headers porque Railway pone HTTPS delante.
# EN: One process: the retention purge runs inside the app and must not be
#     duplicated. --proxy-headers because Railway terminates HTTPS in front.
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
