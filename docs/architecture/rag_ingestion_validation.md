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

La rama #41 es independiente de #40. Tras integrar #40 en dev, sincronizar y validar el intercambio de snapshots; conectar el clasificador de amenazas según contrato. Los textos reales permanecen fuera de la colección oficial hasta confirmar fidelidad y permiso de uso RAG por documento. No publicar corpus ni base vectorial. Los datos sintéticos no constituyen evidencias oficiales.
