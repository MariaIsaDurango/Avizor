# Issue #41 — Validación de ingestión / Ingestion validation

## Decisión técnica aprobada por el equipo

Chunks ordinarios de 450–480 tokens (objetivo 480), solape de 80 y comprobación con tokenizer E5 real, incluyendo prefijos y tokens especiales (máximo 512). Se permiten documentos cortos y fragmentos finales inferiores a 450. Sin truncamiento silencioso.

## Resultados observados en WSL (17/11/2026)

- 26/26 tests específicos, incluidos ChromaDB real y tokenizer E5 en caché.
- 32/32 tests RAG (incluye 6 de #39); cobertura global 76 % antes de ampliar tests.
- Ruff: sin errores antes de la ampliación.
- Corpus sintético: 3 documentos, 9 chunks; mínimo 179, máximo 480 tokens; entrada máxima E5 484.
- Primera ingestión: 3 insertados; siguiente: 0 insertados, 3 actualizados, 9 chunks almacenados.
- Modelo: intfloat/multilingual-e5-base; revisión d128750597153bb5987e10b1c3493a34e5a4502a.

| Consulta | Primer documento recuperado | Distancia coseno |
|---|---|---:|
| SMS falso de una empresa de paquetería | SMS de paquetería simulado | 0.1457 |
| Mi hijo me escribe desde un número nuevo y me pide dinero urgentemente | Familiar en apuros simulado | 0.1683 |
| Me llaman de mi banco y me piden las claves de acceso a mi cuenta | Llamada bancaria simulada | 0.1423 |
| Receta de tortilla de patatas | SMS de paquetería simulado (irrelevante) | 0.2056 |

En tres consultas positivas, los tres primeros fragmentos pertenecen al documento esperado. Bajo esa definición de relevancia, Precision@1 = 1, Precision@3 = 1, Precision@5 = 0.6 y MRR = 1. No son métricas de producción ni de clasificación de fraude. La consulta fuera de dominio devuelve vecinos aunque no haya evidencia pertinente. Calibrar filtros y diversidad por URL en #43; no fijar un umbral de producción con cuatro ejemplos.

## Ampliación de pruebas

`rag/tests/test_issue41_runtime.py`: 20 casos offline con dobles de prueba para carga local del modelo, compatibilidad de API de dimensiones, prefijos, normalización, límite de entrada, vectores inválidos, argumentos CLI y separación de rutas. No descarga pesos ni escribe en la base oficial.

```bash
python -m pytest rag/tests/test_issue41_runtime.py -q
python -m pytest rag/tests -q --tb=short --cov=rag/src --cov-report=term-missing
```

Validación del paquete en entorno de preparación (Python 3.13): 44 passed, 2 skipped (faltan dependencias de integración); cobertura 87 % sobre los módulos #41, embeddings 100 %, pipeline 99 %. Se reprodujo localmente la corrección del warning de API de dimensiones ya aplicada en WSL. No se incluye ese archivo para evitar sobrescribir la versión del usuario. Los resultados definitivos de WSL, Ruff y regresión backend quedan pendientes.

## Integración pendiente

La rama #41 se inició de forma independiente de #40. #40 ya está integrada en dev; en la revisión de #41 se ha sincronizado la rama y se ha preparado la validación conjunta. Sigue pendiente validar el intercambio de snapshots reales y conectar el clasificador de amenazas según contrato. Los textos reales permanecen fuera de la colección oficial hasta confirmar fidelidad y permiso de uso RAG por documento. No publicar corpus ni base vectorial. Los datos sintéticos no constituyen evidencias oficiales.

## Revisión de PR: configuración de CHROMA_PATH (18/11/2026)

- Se incorpora `resolve_official_path()` para respetar la variable de entorno y `.env` de la raíz, con fallback a `rag/chroma_db`.
- Se conserva la ruta sintética independiente; se rechaza el solapamiento entre rutas, incluso mediante enlaces simbólicos.
- Se añaden 15 casos de regresión en `rag/tests/test_issue41_chroma_path.py` y se aísla de la configuración personal la fixture CLI anterior.
- Se declara `python-dotenv` como dependencia directa de RAG. No se modifica el CI, el backend ni el contrato.

### Evidencia de pruebas de preparación (Python 3.13.5)

Entorno reconstruido a partir de los archivos de revisión entregados y el snapshot de dev `46edb6c`, recuperando el fixture sintético del paquete inicial de #41. Sin accesos a fuentes externas ni corpus real.

| Comando | Resultado |
|---|---|
| `python -m pytest rag/tests/test_issue41*.py -q -rs --cov=rag/src/ingestion --cov=rag/src/vector_store --cov-report=term-missing` | 59 passed, 2 skipped; cobertura 87 % |
| `python -m pytest rag/tests -q -rs --cov=rag/src --cov-report=term-missing` | 157 passed, 2 skipped; cobertura 81 % |

La cobertura de `pipeline.py` es 99 %. Las dos omisiones son las pruebas de persistencia real ChromaDB y tokenizer E5 por ausencia de `chromadb` y `transformers` en el entorno de preparación. Los 15 casos de configuración pasan. Los tests de configuración CLI utilizan dobles de prueba, no la colección oficial.

### Validación definitiva en WSL — 18/11/2026

Entorno:

- Windows 11 + WSL2 Ubuntu.
- Python 3.12.3.
- Pytest 9.2.0.
- python-dotenv 1.2.4.

Validación realizada tras integrar los últimos cambios
de dev, incluida la issue #40.

| Validación | Resultado |
|---|---:|
| Tests CHROMA_PATH | 15/15 |
| Tests específicos issue #41 | 61/61 |
| Suite completa RAG | 159/159 |
| Suite completa backend | 278/278 |
| Total tests de regresión | 437 |
| Cobertura issue #41 | 92 % |
| Cobertura global RAG | 83 % |
| Cobertura pipeline | 99 % |
| Ruff check | OK |
| Ruff format | OK |
| Tests fallidos | 0 |
| Tests omitidos | 0 |

Los 15 tests de CHROMA_PATH están incluidos en los
61 tests específicos de la issue #41, que a su vez
forman parte de los 159 tests de la suite RAG.

### Tiempos de ejecución

| Pruebas | Tiempo |
|---|---:|
| Tests CHROMA_PATH | 0,78 s |
| Tests específicos issue #41 | 98,93 s |
| Suite completa RAG | 95,06 s |
| Suite completa backend | 25,46 s |

### Validación de CHROMA_PATH

- Ruta predeterminada verificada.
- Rutas relativas y absolutas.
- Configuración mediante archivo .env.
- Prioridad de variables de entorno sobre .env.
- Rechazo de rutas vacías.
- Protección frente a solapamiento de rutas.
- Protección frente a enlaces simbólicos conflictivos.
- Separación entre corpus oficial y sintético.

### Cobertura por módulo de la issue #41

| Módulo | Cobertura |
|---|---:|
| cleaner.py | 100 % |
| embeddings.py | 100 % |
| pipeline.py | 99 % |
| chroma_store.py | 90 % |
| chunker.py | 86 % |
| models.py | 84 % |
| TOTAL ISSUE #41 | 92 % |

La cobertura global del componente RAG, incluyendo
los desarrollos de las issues #39, #40 y #41,
es del 83 %.

### Comandos ejecutados

    ruff check rag --fix
    ruff format rag
    ruff check rag
    ruff format --check rag
    python -m pytest rag/tests/test_issue41_chroma_path.py -v --tb=short
    python -m pytest rag/tests/test_issue41*.py -q -rs --cov=rag/src/ingestion --cov=rag/src/vector_store --cov-report=term-missing
    python -m pytest rag/tests -q -rs --cov=rag/src --cov-report=term-missing
    python -m pytest backend/tests -q --tb=short

### Limitaciones y siguientes pasos

- El workflow CI todavía no ejecuta la suite RAG.
- Las pruebas descritas se han ejecutado localmente.
- Incorporar RAG al CI en coordinación con QA.
- Validar fidelidad y permisos del corpus oficial.
- Realizar la ingestión definitiva del corpus autorizado.
- Integrar el clasificador de amenazas.
- Calibrar los criterios de recuperación semántica
  en la issue #43.
- Alinear el criterio de chunking en la próxima
  actualización del Contrato Schemas.

Las métricas de recuperación obtenidas sobre el corpus
sintético son preliminares y no constituyen resultados
de producción.