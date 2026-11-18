# Issue #43 — Retrieval y evidencias (fase 1)

Estado: retrieval validado en WSL; núcleo LangGraph y adaptador Ollama implementados en fase 2. Pendiente conectar al backend y medir el flujo real.

## Contrato de recuperación

- Reutiliza `Notice`, `ChromaStore` y `E5Embedder` de #41, con colección `official_notices`, similitud coseno y revisión del modelo exacta.
- `threat_type` conserva su valor original revisado. Opcionalmente, `secondary_threats` es una lista de categorías del contrato revisadas en la aprobación de ese documento (en corpus sintético, en el registro de prueba). No son etiquetas inferidas de títulos ni del LLM.
- Se añaden `is_<threat_type>` y `published_at_day` (ordinal de fecha de calendario, entero, no timestamp Unix). Chroma aplica un AND de etiqueta y límites inclusivos del intervalo de 24 meses, excluyendo fechas futuras. `none` no dispara retrieval.
- `ChromaStore.query` conserva la interfaz anterior y admite `where` y `documents`. Nunca pide más de cinco resultados. El retriever comprueba de nuevo fecha, etiqueta, distancia y procedencia. Umbral inicial configurable de distancia coseno 0,35 (hipótesis a calibrar, no métrica validada).
- La consulta debe llegar anonimizada. E5 conserva su límite de 512 tokens; una consulta demasiado larga falla sin truncarse. El futuro agente deberá capturar los fallos y devolver la vía rápida.
- El constructor verifica modo del corpus y revisión de embeddings. El modo demo solo admite URLs de `example.invalid` y jamás genera evidencia oficial.
- `official_evidence` produce diccionarios `{type: "official_notice", source, url}` a partir de metadatos recuperados, sin intervención del LLM, deduplicados por fuente y URL. La validación final contra el contrato backend queda para la integración. La forma canónica de la URL no prueba por sí sola que el aviso exista o tenga permiso de reutilización.

## Compatibilidad e indexación

Los registros ya almacenados antes de #43 no tienen los nuevos metadatos y no serán seleccionados por el filtro. Reingerir los mismos snapshots aprobados mediante el pipeline #41 actualiza los IDs existentes sin crear una colección diferente. Para el corpus sintético exclusivamente: `python -m rag.src.ingestion.pipeline --synthetic --query "SMS bancario fraudulento"`. No se borra ninguna base de datos.

El corpus oficial conserva la revisión de fidelidad, la referencia de reutilización y la aprobación por URL y hash exactos. Por decisión interna del equipo, se utilizará en un prototipo académico no comercial sin solicitar autorizaciones individuales; esta decisión no es autorización expresa de los titulares. La fase 2 añade un manifiesto local explícito para registrar dicha decisión, sin modificar los snapshots. Los títulos disponibles de DGT, Seguridad Social y paquetería son candidatos a smishing; los de fraude financiero son candidatos a fraude bancario. No se garantiza que contengan un caso específico de smishing bancario hasta revisar sus textos. Se recomienda localizar un aviso específico de INCIBE/OSI si los existentes resultan insuficientes.

## Validación pendiente

- Chroma persistente real y embeddings E5 cacheados en WSL.
- Recuperación efectiva de un aviso oficial sobre smishing bancario con URL verificada.
- Calibración de relevancia y diversidad de resultados, y presupuesto de contexto de Gemma 3 4B.
- LangGraph, validación Verdict, plantillas, evidencias técnicas, privacidad y fallback global inferior a 15 s.

## Fase 2 — política académica y núcleo del agente

El equipo ha decidido utilizar las fuentes en el proyecto académico no comercial, sin solicitar permisos individuales. Se conserva atribución, URL, fecha y hash. La decisión no constituye autorización expresa de los titulares ni una conclusión sobre licencias; no se distribuirán los textos ni la base vectorial con este paquete. Cualquier cambio de finalidad requiere revisar las condiciones aplicables.

### Preparar el corpus local

1. `python -m rag.scripts.prepare_issue43_corpus --output rag/data/processed/issue43_labels.json` crea un borrador local por URL y hash. Incluye las 30 clasificaciones preliminares derivadas de los títulos que se proporcionaron. Revisar las etiquetas con el texto completo; cambiar las categorías del JSON si procede. Los títulos desconocidos reciben `other`, no una etiqueta específica inventada.
2. `python -m rag.scripts.prepare_issue43_corpus --labels rag/data/processed/issue43_labels.json --accept-team-policy --output rag/data/processed/issue43_academic_approvals.json` registra el uso interno decidido por el equipo; el campo `rag_allowed` es una autorización interna de procesamiento, no permiso externo. No sobrescribe el manifiesto, no altera raw y no omite los controles de hash, URL o antigüedad de #41.
3. `python -m rag.src.ingestion.pipeline --input rag/data/raw/incibe_content.json --input rag/data/raw/osi_content.json --input rag/data/raw/banco_espana_content.json --approvals rag/data/processed/issue43_academic_approvals.json` ingiere los tres snapshots textuales conocidos. Policía Nacional dispone solo de metadatos y requiere contenido antes de indexar. El corpus sintético permanece separado.

### LangGraph

`retrieve → choose → validate`: se recuperan hasta cinco fragmentos con la amenaza de la vía rápida; si no hay resultados no se consulta el LLM. El proveedor Ollama está restringido a 127.0.0.1:11434; temperatura cero, schema JSON, hasta 80 tokens de salida, contexto 4096, keep-alive 15 minutos. Las instrucciones se envían en un mensaje system independiente y los datos como un JSON en un mensaje user. No se envían listas de URLs del usuario ni se habilitan herramientas. El texto debe llegar anonimizado; esta etapa no sustituye NER. Por presupuesto inicial, se rechaza texto de más de 1200 caracteres y se usan extractos de hasta 320 caracteres de cada fragmento; no se altera el texto almacenado. No se garantiza que cualquier tokenización quepa en 4096. LangSmith tracing deshabilitado en la invocación.

El LLM devuelve únicamente `block_template` y `references` (índices de fragmentos recuperados), sin URLs, texto libre, nivel, confianza ni acción. Se valida el conjunto permitido y las referencias. El veredicto enriquecido conserva el riesgo, tipo y confianza de la vía rápida; la explicación para el tutor se construye de forma determinista. Las evidencias oficiales se derivan de los metadatos, nunca del LLM. Las evidencias técnicas son una entrada de confianza reservada al futuro adaptador del backend; no se infieren aquí. El resultado se limita a cinco evidencias. No se presentan URLs sintéticas como oficiales. Esta elección conservadora prioriza la seguridad; no permite que el LLM eleve o rebaje el riesgo.

`AgentEngine` devuelve `None` cuando falla la selección, retrieval, modelo o plazo; el futuro adaptador debe devolver la vía rápida guardada. Presupuesto de pared 13 s desde la invocación, 10 s como máximo para HTTP, un único worker por instancia y rechazo mientras está ocupado. Una operación tardía no puede publicar resultados, aunque puede seguir consumiendo CPU hasta terminar; no se promete cancelación inmediata del trabajo nativo. Inicialización de modelos y latencia completa del backend aún no incluidas en esta medida. Sin conexión a endpoints ni persistencia de alertas en fase 2.

### Validación local

`PYTHONPATH=backend:. python -m pytest rag/tests/test_issue43_agent.py rag/tests/test_issue43_academic_corpus.py -v --tb=short -rs`

`PYTHONPATH=backend:. python -m rag.scripts.validate_issue43_agent` utiliza mensajes ficticios y el corpus sintético con Gemma local. `--official` prueba mensajes bancarios con el corpus oficial tras la ingesta. El script valida el `AgentOutput` y construye un `Verdict` de prueba con el schema real, sin escribir alertas. La categoría y el riesgo se suministran explícitamente para la prueba del agente; no son una medición del clasificador. Reporta `enriched` o `fallback` y tiempo de la llamada. El test plan de smishing bancario con avisos oficiales reales sigue pendiente hasta recuperar documentos relevantes y comprobar sus URLs.
