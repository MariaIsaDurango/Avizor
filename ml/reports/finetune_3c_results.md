# Resultados del fine-tuning de 3 clases (#36)

Fecha: 2026-11-21 · Entorno: Google Colab, GPU T4 · Notebook: `ml/notebooks/04_finetune_colab.ipynb`

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
| Latencia CPU (mediana) | 247 ms | 270 ms |

## Objetivos

| Objetivo | Resultado |
|---|---|
| SMS: recall de sospechosos ≥ 80 % | Cumplido (91 %) |
| Email: recall de fraud ≥ 95 % | No cumplido (92,7 %) |
| Latencia < 500 ms en CPU | Cumplido (270 ms) |

## Limitaciones

- El test de email tiene unos 200 mensajes: la diferencia entre 0.936 y 0.927 es un mensaje.
- SpamSpa solo tiene 62 estafas; el test de SMS tiene unas 9, así que las métricas de `fraud` en SMS varían mucho entre ejecuciones.
- SpamSpa parece sintético: no tiene URLs ni teléfonos. Conviene añadir SMS de estafa realistas basados en avisos de INCIBE y OSI.

## Siguiente paso (#38)

En lugar de elegir la clase más probable, marcar `fraud` cuando su probabilidad supere un umbral calibrado con el conjunto de validación, para acercarse al 95 % de recall sin disparar los falsos positivos. Exportar el modelo a ONNX int8 e integrarlo en el backend como `MlClassifier`.
