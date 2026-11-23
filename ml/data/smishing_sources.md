# Smishing Dataset — Fuentes y proceso de generación (#146)

## Fuentes primarias de contexto (RAG corpus)

| Fuente | Fragmentos | Descripción |
|--------|-----------|-------------|
| INCIBE | 57 | Alertas del Instituto Nacional de Ciberseguridad |
| OSI | 50 | Avisos de la Oficina de Seguridad del Internauta |
| Banco de España | 15 | Comunicados sobre fraude financiero |
| **Total** | **122** | Almacenados en `rag/chroma_db` → colección `official_notices` |

## Proceso de generación

1. Se recuperan los 122 fragmentos con `col.get()` (embeddings BERT 768-dim incompatibles con all-MiniLM-L6-v2).
2. Para cada entidad se selecciona contexto por puntuación de palabras clave + términos de fraude (`smishing`, `phishing`, `estafa`, etc.), máx. 3000 caracteres.
3. Se llama a Groq (`openai/gpt-oss-120b` o `qwen/qwen3.8-27b`, `temperature=0.9`) con un SYSTEM prompt que exige:
   - SMS < 160 caracteres
   - Enlace falso incluido
   - Español de España (tuteo o ustedeo)
   - Tono urgente (multa, paquete retenido, cuenta bloqueada…)
4. Se filtran líneas fuera del rango 20–200 caracteres.
5. Pausa de 2 s entre llamadas (rate limit del free tier de Groq).

**Script:** `ml/scripts/generate_smishing.py`

**Comando de ejecución:**

```bash
GROQ_API_KEY=sk-... python scripts/generate_smishing.py \
    --chroma ../../rag/chroma_db \
    --out data/raw/smishing_groq.csv \
    --per-entity 10 \
    --model gemma2-9b-it
```

## Entidades suplantadas (10)

- Correos de España
- Banco Santander
- BBVA
- CaixaBank
- Agencia Tributaria (AEAT / Hacienda)
- Dirección General de Tráfico (DGT)
- Seguridad Social
- Iberdrola
- Policía Nacional
- Amazon España

## Formato de salida

CSV con columnas `text`, `label`, `source`, compatible con `load_spamspa()`:

```
text,label,source
"Su paquete de Correos está retenido...",fraud,smishing-groq
```

## Volumen generado

~77 SMS de 10 entidades (filtrado de refusals, URLs truncadas y mensajes fuera de rango 20–200 chars).

## Revisión manual

Antes de incorporar al entrenamiento, revisar al menos el 20% de la muestra (≥ 20 SMS):

- Confirmar que el texto es < 160 caracteres.
- Verificar que el enlace es claramente falso (dominio inventado).
- Descartar cualquier mensaje que incluya información personal real.
- Anotar en esta sección la fecha de revisión y el revisor.

**Revisión completada** — 2026-11-23, revisado por Majo (MaríaJosé). Muestra verificada: enlaces falsos presentes, español de España, sin datos personales reales.

## Integración en el entrenamiento

Una vez revisado manualmente, añadir `smishing_groq.csv` como fuente extra en `04_finetune_colab.ipynb`:

```python
smishing = load_spamspa("data/raw/smishing_groq.csv")
frames = [spaphish, spamspa, smishing]
data = prepare(frames)
```
