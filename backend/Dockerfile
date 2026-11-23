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
ENV PYTHONPATH=/app:/app/backend

# ES: Primero las dependencias (capa en caché si no cambian).
# EN: Dependencies first (cached layer while they do not change).
COPY backend/requirements.txt ./requirements.txt

COPY rag/requirements.txt /app/rag/requirements.txt
RUN pip install -r requirements.txt -r /app/rag/requirements.txt

# Modelo E5 precargado para el RAG sin descarga al arrancar.
ENV HF_HOME=/app/huggingface
RUN python -c "from pathlib import Path; from huggingface_hub import snapshot_download; p=Path(snapshot_download('intfloat/multilingual-e5-base', revision='main')); assert p.name == 'd128750597153bb5987e10b1c3493a34e5a4502a', f'Revision E5 incompatible: {p.name}'; print('E5 listo:', p.name)"

# ES: Modelo de IA (#38), opcional. No está en el repo (111 MB): se descarga de
#     una release de GitHub y se comprueba su SHA-256. Sin estas variables la
#     imagen se construye igual y usa el clasificador por reglas. Va antes
#     del código para no descargarlo otra vez en cada cambio.
# EN: AI model (#38), optional. Not in the repo (111 MB): downloaded from a
#     GitHub release and checked against its SHA-256. Without these variables
#     the image still builds and uses the rule-based classifier.
#     Before the code, so a code change does not download it again.
ARG ML_MODEL_URL=""
ARG ML_MODEL_SHA256=""
COPY backend/scripts/fetch_model.py ./scripts/fetch_model.py
RUN python scripts/fetch_model.py /app/models/avizor-3c-onnx
ENV ML_MODEL_DIR=/app/models/avizor-3c-onnx

# ES: Solo lo necesario para ejecutar: sin tests, sin móvil, sin ml.
# EN: Only what is needed at runtime: no tests, no mobile, no ml.
COPY backend/alembic.ini ./alembic.ini
COPY backend/migrations ./migrations
COPY backend/app ./app
COPY backend/docker-entrypoint.sh ./docker-entrypoint.sh
COPY rag/src /app/rag/src
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
