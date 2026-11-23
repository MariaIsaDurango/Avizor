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
3. Se llama a Groq (`openai/gpt-oss-120b`, `temperature=0.9`) con un SYSTEM prompt que exige:
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

CSV con columnas `text`, `label`, `source`. Se carga con `load_synthetic()` (`ml/src/classifier/data.py`):

```
text,label,source
"Su paquete de Correos está retenido...",fraud,smishing-groq
```

## Volumen generado

247 SMS de 10 entidades. Filtros aplicados: refusals en inglés, acortadores reales (amzn.to, bit.ly…), dominios oficiales (.gov.es, .gob.es), URLs malformadas, SMS fuera del rango 20–160 caracteres.

## Revisión manual

Antes de incorporar al entrenamiento, revisar al menos el 20% de la muestra (≥ 20 SMS):

- Confirmar que el texto es < 160 caracteres.
- Verificar que el enlace es claramente falso (dominio inventado).
- Descartar cualquier mensaje que incluya información personal real.
- Anotar en esta sección la fecha de revisión y el revisor.

**Revisión completada** — 2026-11-23, revisado por Majo (MaríaJosé). Muestra verificada: enlaces falsos presentes, español de España, sin datos personales reales.

## Integración en el entrenamiento

Los SMS sintéticos se usan **solo para entrenar**. Validación y test siguen siendo
los datos reales (SpaPhish y SpamSpa), con los mismos splits de siempre, para que
los resultados se puedan comparar con el modelo anterior sin inflarlos.

```bash
python -m src.classifier.train \
    --spaphish "data/raw/spaphish/Spaphish dataset - DiB.csv" \
    --spamspa data/raw/spamspa/train.csv \
    --review data/raw/spamspa/spamspa_review.csv \
    --synthetic data/raw/smishing_groq.csv \
    --synthetic data/raw/smishing_no_link_groq.csv \
    --synthetic data/raw/legit_links_groq.csv \
    --real-test data/raw/smishing_real_test.csv \
    --out models/avizor-3c
```

El notebook `04_finetune_colab.ipynb` ya lo incluye. `export.py` necesita el mismo
`--synthetic` para reconstruir los splits.

Riesgo vigilado: todos los SMS sintéticos llevan enlace y los SMS reales de SpamSpa
no. En el primer entrenamiento solo con `smishing_groq.csv` (estafas), 96 de 118 SMS
reales normales o de publicidad pasaron a `fraud` solo por añadirles un enlace. Por eso
se añadió `legit_links_groq.csv` (etiqueta `ham` = `none`). Con 222 SMS legítimos el
atajo desapareció (0 de 118), pero el modelo no mejoró en los SMS reales. Segunda versión:

- `legit_links_groq.csv` ampliado a 593 SMS legítimos con enlace, incluidos dominios
  poco conocidos (clínicas, farmacias, gestorías, tiendas), para que el modelo no
  aprenda "dominio desconocido = estafa".
- `smishing_no_link_groq.csv`: 247 estafas **sin enlace** (premios, herencias, cuenta
  bloqueada, códigos OTP, "hijo en apuros", Hacienda), del mismo estilo que las de
  SpamSpa. `metrics.json` incluye `link_probe`: cuántos SMS reales normales o de publicidad
pasan a `fraud` solo por añadirles un enlace neutro.

## Medición aparte

- El 20 % de los SMS sintéticos (por fuente y etiqueta) no se usa para entrenar: queda en
  `synthetic_test` para medir avisos legítimos con enlace y estafas modernas.
- `smishing_real_test.csv` (25 estafas reconstruidas a partir de avisos de INCIBE y OSI)
  solo se usa para medir (`--real-test`), nunca para entrenar.
- Ambos resultados aparecen en `metrics.json` → `extra_tests`.
