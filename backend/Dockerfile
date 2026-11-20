# ES: Imagen del backend (FastAPI + portal web). Se construye desde la RAÍZ del
#     repo porque el backend importa rag/src/reputation (#42).
#       docker build -f backend/Dockerfile -t avizor-backend .
# EN: Backend image (FastAPI + web portal). Built from the repo ROOT because
#     the backend imports rag/src/reputation (#42).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

# ES: Primero las dependencias (capa en caché si no cambian).
# EN: Dependencies first (cached layer while they do not change).
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# ES: Solo lo necesario para ejecutar: sin tests, sin móvil, sin ml.
# EN: Only what is needed at runtime: no tests, no mobile, no ml.
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY backend/app ./app
COPY backend/docker-entrypoint.sh ./docker-entrypoint.sh
COPY rag/src/reputation /app/rag/src/reputation
COPY rag/data/reputation /app/rag/data/reputation

# ES: Sin root dentro del contenedor. EN: No root inside the container.
# ES: sed quita CRLF por si el script se copió desde Windows.
# EN: sed strips CRLF in case the script was copied from Windows.
RUN useradd --create-home --uid 10001 avizor \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && chown -R avizor:avizor /app
USER avizor

# ES: Railway define PORT; en local se usa 8000.
# EN: Railway sets PORT; 8000 is used locally.
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
