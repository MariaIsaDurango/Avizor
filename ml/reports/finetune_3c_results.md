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

| Métrica (test, datos reales) | Modelo en producción | + 247 estafas sintéticas | + 247 estafas y 222 legítimos con enlace | + 494 estafas (con y sin enlace) y 593 legítimos |
|---|---|---|---|---|
| Prueba de enlaces (sin → con enlace) | no medida | 1 → **96** | 2 → **0** | 2 → **0** |
| SMS: recall de fraud | **0.667** | 0.444 | 0.444 | 0.444 |
| SMS: precisión de fraud | 0.667 | 0.800 | 0.667 | 0.667 |
| SMS: recall de sospechosos | **0.91** | 0.91 | 0.881 | 0.896 |
| SMS: macro F1 | **0.827** | 0.801 | 0.780 | 0.780 |
| Email: recall de fraud | 0.927 | 0.945 | 0.936 | 0.927 |
| Email: precisión de fraud | **0.953** | 0.928 | 0.927 | **0.953** |

**Conclusiones**

- Solo con estafas sintéticas, el modelo aprendió el atajo del enlace: 96 de 118 SMS reales legítimos pasaban a `fraud` con un enlace. Ese modelo se descartó.
- Con los SMS legítimos con enlace (`legit_links_groq.csv`), el atajo desaparece (0 de 118).
- Aun así, en los SMS reales de SpamSpa ninguna de las dos versiones mejora al modelo en producción: el recall de estafas baja de 6 a 4 de las 9 estafas del test. Con tan pocas estafas la diferencia es pequeña, pero no hay evidencia de mejora.
- Tercera versión (`smishing_no_link_groq.csv` y `legit_links_groq.csv` ampliado a 593): sin atajo del enlace y el email queda igual que el modelo en producción. En SMS sigue en 4 de 9.
- El test solo tiene 9 estafas reales por SMS, casi todas sorteos y concursos ("Participa en nuestro concurso y gana premios increíbles", "Gana un iPhone gratis participando en este sorteo") cuya frontera entre publicidad y estafa es difusa. El primer entrenamiento sin sintéticos (peso de fraud 2.0) también dio 4 de 9, así que la diferencia entre 4 y 6 de 9 está dentro de la variación normal entre entrenamientos: este test no permite saber si los sintéticos mejoran o empeoran.
- Causa probable: las estafas de SpamSpa son mensajes cortos sin enlace ("Haz clic para reclamar tu premio") y las sintéticas imitan campañas reales con entidad y enlace. Este test no mide bien ese segundo tipo.

### Cuarta versión: medición con mensajes no vistos (2026-11-23)

Datasets actualizados por Majo y dos mediciones nuevas que **nunca** se usan para entrenar:

- `synthetic_test`: el 20 % de los SMS sintéticos (69 legítimos con enlace y 96 estafas modernas), separado por fuente y etiqueta.
- `real_test`: `smishing_real_test.csv`, 25 estafas reconstruidas a partir de avisos de INCIBE y OSI.

El modelo en producción se midió con los mismos mensajes (ONNX int8, umbral 0.36).

| Medición | Modelo en producción | Cuarta versión |
|---|---|---|
| Legítimos con enlace marcados como estafa (synthetic_test) | **43 de 69** | **1 de 69** |
| Estafas modernas detectadas (synthetic_test) | 89 de 96 | **95 de 96** |
| Smishing real detectado (real_test) | 24 de 25 | **25 de 25** |
| Prueba de enlaces (SMS reales, sin → con enlace) | no medida | 3 → 0 |
| SMS reales: recall / precisión de fraud | 0.667 / 0.667 | 0.667 / 0.667 |
| SMS reales: precisión de spam | 0.912 | **0.945** |
| SMS reales: macro F1 | 0.827 | **0.838** |
| Email: recall / precisión de fraud | 0.927 / **0.953** | 0.927 / 0.944 |

Lectura:

- El modelo en producción marca como estafa la mayoría de los avisos legítimos con enlace (bancos, Correos, AEAT...). Lo aprendió de los correos de phishing de SpaPhish, que llevan enlaces. El test principal no lo detectaba porque SpamSpa no tiene SMS con enlace.
- La cuarta versión corrige ese problema y detecta igual o mejor las estafas, sin empeorar en SMS reales. En email la precisión baja ligeramente (unos 2 mensajes de 200).
- Limitaciones: `synthetic_test` sale del mismo generador que los datos de entrenamiento, así que puede ser optimista; `real_test` solo tiene estafas (no mide falsos positivos con SMS legítimos reales). Los resultados de la cuarta versión son sin umbral; falta exportarla a ONNX y calibrar su umbral.

### Cuarta versión exportada a ONNX int8

`beto-3c-20261123-onnx-int8`: ONNX coincide con torch (diferencia 3e-9), int8 coincide con fp32 en el 98,8 % de las predicciones, 111 MB y 35 ms por mensaje en CPU.

**Umbral de fraud:** con este modelo ningún umbral llega al 95 % de recall en validación (máximo 112 de 118). La calibración elegía entonces el mínimo (0.05), que añade falsos positivos sin detectar más estafas. Se corrigió `calibrate_fraud_threshold`: si no se alcanza el objetivo, devuelve el umbral más alto con el mejor recall posible. Resultado: **0.30**. Con el modelo en producción la calibración no cambia (0.36).

| Medición (int8 con su umbral) | Producción (0.36) | Cuarta versión (0.30) |
|---|---|---|
| Legítimos con enlace marcados como estafa (synthetic_test) | 43 de 69 | **1 de 69** |
| Estafas modernas detectadas (synthetic_test) | 89 de 96 | **95 de 96** |
| Smishing real detectado (real_test) | 24 de 25 | **25 de 25** |
| SMS reales: recall / precisión de fraud | 0.667 / 0.667 | **0.778 / 0.700** |
| SMS reales: recall de sospechosos | 0.91 | **0.94** |
| Email: recall / precisión de fraud | 0.927 / **0.953** | **0.936** / 0.944 |

**Estado:** pendiente de decidir con el equipo. Recomendación: exportar la cuarta versión, calibrar su umbral y repetir estas mediciones con el modelo ONNX antes de sustituir el de producción. Mientras tanto sigue en producción `beto-3c-20261121-onnx-int8`. Se conservan el código (`load_synthetic`, `build_splits`, `--synthetic`, `link_probe`) y los dos CSV.

**Mejoras propuestas:** un conjunto de test con smishing **real** (por ejemplo, los textos de estafas citados en los avisos de INCIBE y OSI del corpus del RAG) para medir si los SMS sintéticos mejoran la detección de campañas reales.
