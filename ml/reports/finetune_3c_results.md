# Resultados del fine-tuning de 3 clases (#36)

Fecha: 2026-11-21 · Versión: `beto-3c-20261121` · Entorno: Google Colab, GPU T4 · Notebook: `ml/notebooks/04_finetune_colab.ipynb`

## Configuración

| Parámetro | Valor |
|---|---|
| Modelo base | `dccuchile/bert-base-spanish-wwm-cased` (BETO) |
| Clases | `none` (GREEN), `spam` (AMBER), `fraud` (RED) |
| Datos | SpaPhish (email) + SpamSpa (SMS), anonimizados con las mismas reglas que el móvil (`regex-v0`) y sin duplicados |
| Revisión SpamSpa | 449 mensajes "spam" revisados a mano por Isa y Majo: 387 publicidad (`spam`), 62 estafa (`fraud`) |
| División | 70 / 15 / 15 estratificada por fuente y clase (`random_state=42`) |
| Épocas | 5, con early stopping (paciencia 2) por macro F1 |
| Peso de `fraud` | 3.0 |

Modelos descartados: `PlanTL-GOB-ES/roberta-base-bne` (su tokenizer no carga con transformers 5) y `BSC-LT/roberta-base-bne` (retirado de Hugging Face).

## Resultados en test

| Métrica | Peso fraud 2.0 | **Peso fraud 3.0 (elegido)** |
|---|---|---|
| Email: recall de fraud | 0.936 | 0.927 |
| Email: precisión de fraud | 0.953 | 0.953 |
| Email: accuracy | 0.943 | 0.938 |
| SMS: recall de sospechosos (spam + fraud) | 0.91 | 0.91 |
| SMS: recall de fraud | 0.444 | 0.667 |
| SMS: precisión de fraud | 0.571 | 0.667 |
| SMS: macro F1 | 0.772 | 0.827 |
| Latencia CPU (mediana) | 247 ms | 283 ms |

## Objetivos

| Objetivo | Resultado |
|---|---|
| SMS: recall de sospechosos ≥ 80 % | Cumplido (91 %) |
| Email: recall de fraud ≥ 95 % | No cumplido (92,7 %) |
| Latencia < 500 ms en CPU | Cumplido (283 ms) |

## Limitaciones

- El test de email tiene unos 200 mensajes: la diferencia entre 0.936 y 0.927 es un mensaje.
- SpamSpa solo tiene 62 estafas; el test de SMS tiene unas 9, así que las métricas de `fraud` en SMS varían mucho entre ejecuciones.
- SpamSpa parece sintético: no tiene URLs ni teléfonos. Conviene añadir SMS de estafa realistas basados en avisos de INCIBE y OSI.

## Siguiente paso (#38)

En lugar de elegir la clase más probable, marcar `fraud` cuando su probabilidad supere un umbral calibrado con el conjunto de validación, para acercarse al 95 % de recall sin disparar los falsos positivos. Exportar el modelo a ONNX int8 e integrarlo en el backend como `MlClassifier`.

## Experimento con SMS sintéticos (#146)

Fecha: 2026-11-23 · Mismos datos reales, mismos splits de validación y test, mismo modelo base (BETO) y peso de fraud 3.0. Los SMS sintéticos (generados con Groq por Majo) se añaden **solo al entrenamiento**.

**Prueba de enlaces (`link_probe`):** de los 118 SMS reales normales o de publicidad del test, cuántos se clasifican como `fraud` sin enlace y al añadirles un enlace neutro (`https://www.ejemplo.es/info`). Detecta si el modelo aprendió "SMS con enlace = estafa".

| Métrica (test, datos reales) | Modelo en producción | + 247 estafas sintéticas | + 247 estafas y 222 legítimos con enlace |
|---|---|---|---|
| Prueba de enlaces (sin → con enlace) | no medida | 1 → **96** | 2 → **0** |
| SMS: recall de fraud | **0.667** | 0.444 | 0.444 |
| SMS: precisión de fraud | 0.667 | 0.800 | 0.667 |
| SMS: recall de sospechosos | **0.91** | 0.91 | 0.881 |
| SMS: macro F1 | **0.827** | 0.801 | 0.780 |
| Email: recall de fraud | 0.927 | 0.945 | 0.936 |
| Email: precisión de fraud | **0.953** | 0.928 | 0.927 |

**Conclusiones**

- Solo con estafas sintéticas, el modelo aprendió el atajo del enlace: 96 de 118 SMS reales legítimos pasaban a `fraud` con un enlace. Ese modelo se descartó.
- Con los SMS legítimos con enlace (`legit_links_groq.csv`), el atajo desaparece (0 de 118).
- Aun así, en los SMS reales de SpamSpa ninguna de las dos versiones mejora al modelo en producción: el recall de estafas baja de 6 a 4 de las 9 estafas del test. Con tan pocas estafas la diferencia es pequeña, pero no hay evidencia de mejora.
- Causa probable: las estafas de SpamSpa son mensajes cortos sin enlace ("Haz clic para reclamar tu premio") y las sintéticas imitan campañas reales con entidad y enlace. Este test no mide bien ese segundo tipo.

**Estado:** pendiente de decidir con Majo. Mientras tanto sigue en producción `beto-3c-20261121-onnx-int8`. Se conservan el código (`load_synthetic`, `build_splits`, `--synthetic`, `link_probe`) y los dos CSV.

**Mejoras propuestas:** un conjunto de test con smishing **real** (por ejemplo, los textos de estafas citados en los avisos de INCIBE y OSI del corpus del RAG) para medir si los SMS sintéticos mejoran la detección de campañas reales.
