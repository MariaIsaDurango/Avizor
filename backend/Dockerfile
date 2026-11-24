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
RUN pip install -r requirements.txt

# ES: RAG (#143), opcional. Desactivado por defecto: torch y el modelo E5 suman
#     varios GB y solo hacen falta con AVIZOR_RAG_ENABLED=true y el volumen de
#     ChromaDB listo. Activar con INSTALL_RAG=true (variable de Railway o
#     --build-arg). torch se instala en versión CPU (sin CUDA). E5 se descarga
#     en la revisión fija que usa la base ChromaDB y se registra como "main"
#     para que E5Embedder() la cargue sin conexión. Solo se descargan los archivos
#     que usa sentence-transformers (sin copias ONNX/OpenVINO ni pytorch_model.bin);
#     la lista debe coincidir con E5_FILES de rag/src/vector_store/embeddings.py.
#     pytest no entra en la imagen.
# EN: RAG (#143), optional and off by default: torch and E5 add several GB and
#     are only needed with AVIZOR_RAG_ENABLED=true and the ChromaDB volume ready.
#     Enable with INSTALL_RAG=true. CPU-only torch. E5 is pinned to the revision
#     used by the ChromaDB store and registered as "main" for offline loading.
#     Only the files sentence-transformers needs (no ONNX/OpenVINO/.bin copies).
ARG INSTALL_RAG=false
ARG E5_REVISION=d128750597153bb5987e10b1c3493a34e5a4502a
ENV HF_HOME=/app/huggingface
COPY rag/requirements.txt /app/rag/requirements.txt
RUN if [ "$INSTALL_RAG" = "true" ]; then \
        pip install torch --index-url https://download.pytorch.org/whl/cpu \
        && grep -v '^pytest' /app/rag/requirements.txt > /tmp/rag-requirements.txt \
        && pip install -r /tmp/rag-requirements.txt \
        && python -c "from huggingface_hub import snapshot_download; snapshot_download('intfloat/multilingual-e5-base', revision='$E5_REVISION', allow_patterns=['*.json', 'model.safetensors', 'sentencepiece.bpe.model'])" \
        && mkdir -p "$HF_HOME/hub/models--intfloat--multilingual-e5-base/refs" \
        && printf '%s' "$E5_REVISION" > "$HF_HOME/hub/models--intfloat--multilingual-e5-base/refs/main" \
        && python -c "from pathlib import Path; from huggingface_hub import snapshot_download; p = Path(snapshot_download('intfloat/multilingual-e5-base', revision='main', local_files_only=True, allow_patterns=['*.json', 'model.safetensors', 'sentencepiece.bpe.model'])); assert p.name == '$E5_REVISION', p.name; print('E5 ready:', p.name)"; \
    else \
        echo "RAG not installed (INSTALL_RAG=$INSTALL_RAG)"; \
    fi

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

# ES: Con RAG, comprueba que E5 carga sin conexión con los archivos descargados.
# EN: With RAG, check E5 loads offline with the downloaded files.
RUN if [ "$INSTALL_RAG" = "true" ]; then \
        python -c "from rag.src.vector_store.embeddings import E5Embedder; e = E5Embedder(); print('E5 loads:', e.revision, len(e.encode(['prueba'])[0]))"; \
    fi

# ES: Sin root dentro del contenedor. EN: No root inside the container.
# ES: sed quita CRLF por si el script se copió desde Windows.
# EN: sed strips CRLF in case the script was copied from Windows.
# ES: E5 (/app/huggingface) solo se lee: cambiarle el dueño duplicaría sus GB en
#     una capa nueva. EN: E5 is read-only; chown would duplicate its GB in a new layer.
RUN useradd --create-home --uid 10001 avizor \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && find /app -path /app/huggingface -prune -o -exec chown avizor:avizor {} +
USER avizor

# ES: Railway define PORT; en local se usa 8000.
# EN: Railway sets PORT; 8000 is used locally.
ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
