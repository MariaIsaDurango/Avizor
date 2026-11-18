# Investigación y comparación de datasets para Avizor

**Estado:** Investigación inicial  
**Objetivo:** Identificar fuentes de datos adecuadas para desarrollar y evaluar los sistemas de detección de amenazas digitales de Avizor.

---

## 1. Objetivo de la investigación

Avizor pretende ayudar a personas mayores a identificar posibles amenazas digitales. Estas amenazas pueden llegar a través de SMS, notificaciones, aplicaciones de mensajería, correos electrónicos, enlaces, imágenes, documentos y comunicaciones telefónicas.

Por este motivo, la investigación no debe limitarse a encontrar un único dataset. Es necesario estudiar diferentes fuentes de datos y determinar qué tipo de amenaza y modalidad cubre cada una.

El objetivo inicial es:

- Identificar datasets públicos relevantes.
- Comparar idioma, formato, etiquetas, tamaño y licencia.
- Evaluar su utilidad para el proyecto.
- Detectar limitaciones y posibles problemas de calidad.
- Seleccionar fuentes para preparar un primer conjunto de entrenamiento y evaluación.
- Definir una estrategia de clasificación que permita incorporar diferentes modalidades.

## 2. Comparativa inicial de datasets

### 2.1. SpamSpa

**Fuente:** [Hugging Face – SpamSpa](https://huggingface.co/datasets/Gabrielaz/spamspa)

| Característica | Información |
|---|---|
| Tipo | Mensajes de spam y no spam |
| Idioma | Español |
| Formato | CSV |
| Variables principales | `text`, `label` |
| Etiquetas | 1 = spam; 0 = no spam |
| Licencia declarada | Apache 2.0 |
| Modalidad | Texto |

**Descripción**

SpamSpa es un conjunto de mensajes en español etiquetados como spam o no spam. Está orientado a tareas de clasificación binaria de texto.

La ficha del dataset indica que sus fuentes incluyen SMS Spam Collection Dataset y SMS Validation Dataset.

**Ventajas**
- Está en español.
- Tiene una estructura sencilla.
- Puede servir para desarrollar un primer clasificador de mensajes.
- La ficha declara licencia Apache 2.0.

**Limitaciones y comprobaciones pendientes**
- No debemos asumir que todos los mensajes representan intentos de phishing o fraude: spam y phishing no son exactamente lo mismo.
- Hay que comprobar el número real de registros y la distribución de etiquetas.
- Es necesario revisar duplicados y posibles solapamientos con sus fuentes originales.
- Conviene verificar la procedencia y las condiciones de reutilización de los datos originales.

**Valoración inicial:** candidato para ampliar el entrenamiento de clasificación de spam en español, pendiente de auditoría de calidad y procedencia.

### 2.2. SpaPhish

**Fuente:** [Mendeley Data – SpaPhish, versión 5](https://data.mendeley.com/datasets/hz2d6gz7pc/5)  
**DOI:** 10.17632/hz2d6gz7pc.5

| Característica | Información |
|---|---|
| Tipo | Correos electrónicos legítimos y phishing |
| Idioma | Español |
| Registros | 1.395 |
| Phishing | 731 |
| Legítimos | 664 |
| Variables | 47 |
| Licencia | CC BY 4.0 |
| Modalidad | Texto y metadatos de correo |

**Descripción**

SpaPhish es un corpus de correos electrónicos en español recopilados de buzones personales e institucionales de los autores. Los mensajes abarcan el periodo 2014–2025 y han sido anonimizados.

Incluye:
- Asunto y cuerpo del correo.
- Etiqueta binaria de clasificación.
- Información técnica derivada, como URLs, número de enlaces y adjuntos.
- Anotaciones sobre técnicas de persuasión e ingeniería social.

Las anotaciones psicológicas contemplan cinco dimensiones: autoridad, prueba social, simpatía/similitud y engaño, compromiso/integridad/reciprocidad y distracción.

**Ventajas**
- Es una fuente directamente relacionada con el phishing.
- Los mensajes están escritos originalmente en español.
- Incluye ejemplos legítimos y maliciosos.
- Permite investigar señales lingüísticas y técnicas.
- Las anotaciones de ingeniería social pueden ayudar a estudiar cómo se construyen los mensajes fraudulentos.

**Limitaciones**
- Está centrado en correo electrónico, no en SMS, llamadas o mensajes de WhatsApp.
- Su tamaño es relativamente reducido para entrenar modelos complejos desde cero.
- No representa necesariamente los mensajes fraudulentos dirigidos específicamente a personas mayores.
- Será necesario revisar el significado exacto de las etiquetas y las columnas antes de incorporarlo al entrenamiento.

**Valoración inicial:** candidato prioritario para el primer clasificador de phishing en español.

### 2.3. UCI SMS Spam Collection

**Fuente:** [UCI Machine Learning Repository – SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)  
**DOI:** 10.24432/C5CC84

| Característica | Información |
|---|---|
| Tipo | SMS legítimos y spam |
| Idioma | Principalmente inglés |
| Registros | 5.574 |
| Licencia | CC BY 4.0 |
| Etiquetas | `ham` y `spam` |
| Modalidad | Texto |

**Descripción**

Es un conjunto de mensajes SMS etiquetados como legítimos (`ham`) o spam. Se creó a partir de varias fuentes, entre ellas mensajes de spam recopilados de un foro británico y mensajes legítimos procedentes de corpus académicos.

**Ventajas**
- Es un dataset conocido y utilizado en investigación.
- Tiene más registros que SpaPhish.
- Puede servir como referencia para desarrollar y comparar modelos de clasificación.
- Su licencia permite compartir y adaptar los datos con atribución.

**Limitaciones**
- Está compuesto principalmente por mensajes en inglés.
- Parte de los mensajes procede de contextos y épocas anteriores a las amenazas actuales.
- La etiqueta spam no equivale necesariamente a phishing o fraude.
- No debe mezclarse directamente con datos en español sin estudiar antes las diferencias lingüísticas.

**Valoración inicial:** útil como conjunto complementario para experimentación y comparación, pero no como fuente principal del modelo en español.

### 2.4. Sting9

**Fuentes:**
- [Sting9 – Dataset](https://sting9.org/dataset)
- [Sting9 – Licencia](https://sting9.org/license)
- [Sting9 – GitHub](https://github.com/sting9-research/dataset)

| Característica | Información |
|---|---|
| Tipo | Phishing, smishing y estafas |
| Canales declarados | Email, SMS, WhatsApp, Telegram, Signal y otros |
| Idiomas | Multilingüe, según los campos de la plataforma |
| Datos | Mensajes anonimizados y metadatos |
| Licencia | Información contradictoria: CC0 en una página y ODC-BY-NC en las condiciones y licencia |

**Descripción**

Sting9 es una iniciativa que recopila mensajes sospechosos de diferentes canales digitales. Su esquema contempla campos como tipo de mensaje, contenido, nivel de amenaza, tipo de ataque e idioma detectado.

**Ventajas**
- Su planteamiento contempla diferentes canales de comunicación.
- Incluye categorías de ataques más específicas que una clasificación simple de spam/no spam.
- Puede aportar ejemplos de smishing y otras estafas.

**Limitaciones**
- Existe una contradicción entre la página del dataset, que indica CC0, y la página de licencia y condiciones, que establecen ODC-BY-NC.
- La licencia ODC-BY-NC restringe el uso comercial y el entrenamiento de modelos destinados a productos comerciales.
- Antes de utilizarlo hay que aclarar las condiciones aplicables a la descarga concreta y al uso previsto por Avizor.
- Es necesario comprobar el volumen real, la calidad de las etiquetas y la distribución por idioma y canal.

**Valoración inicial:** interesante para investigación, pero no se incorporará al entrenamiento hasta aclarar por escrito las condiciones de licencia.

### 2.5. PhishBench-External

**Fuente:** [Mendeley Data – PhishBench-External](https://data.mendeley.com/datasets/2ctjcnm9kn)

| Característica | Información |
|---|---|
| Tipo | URLs de phishing y legítimas |
| Registros | 1.000 |
| URLs de phishing | 500 |
| URLs legítimas | 500 |
| Licencia | CC BY 4.0 |
| Modalidad | URLs |

**Descripción**

Es un conjunto equilibrado de URLs recopiladas para validar sistemas de detección de phishing.

**Ventajas**
- Está específicamente orientado a la detección de enlaces maliciosos.
- Tiene una distribución equilibrada entre URLs de phishing y legítimas.
- Puede utilizarse para experimentar con características de URLs.

**Limitaciones**
- No contiene mensajes completos.
- No permite detectar por sí solo técnicas de manipulación lingüística.
- El conjunto es pequeño.
- Debe revisarse la fecha de recopilación y la disponibilidad actual de los dominios antes de interpretar los resultados.

**Valoración inicial:** candidato para un módulo independiente de análisis de URLs, no para el clasificador principal de mensajes.

---

## 3. Comparación y selección inicial

| Dataset | Idioma | Amenaza principal | Modalidad | Decisión inicial |
|---|---|---|---|---|
| SpamSpa | Español | Spam | Texto | Evaluar e incorporar si supera la auditoría |
| SpaPhish | Español | Phishing | Email y metadatos | Prioritario |
| UCI SMS Spam | Inglés | Spam | SMS | Complementario |
| Sting9 | Multilingüe | Phishing, smishing y estafas | Varios canales | Pendiente de licencia |
| PhishBench-External | No centrado en idioma | URLs de phishing | URL | Candidato para módulo separado |

La selección no implica que todos los datasets deban combinarse. Sus etiquetas y objetivos son diferentes y será necesario normalizarlos cuidadosamente.

## 4. Propuesta de arquitectura de análisis multimodal

El hecho de que Avizor deba analizar diferentes tipos de contenido no significa que sea necesario entrenar un modelo distinto para cada formato.

Se propone una arquitectura por etapas:

1. **Recepción del contenido:** texto, SMS, notificaciones, correo, imagen, audio, vídeo, documento o URL.
2. **Extracción y normalización:** convertir el contenido a formatos analizables.
3. **Clasificación del texto:** analizar mensajes y textos extraídos.
4. **Análisis de URLs:** evaluar enlaces mediante características y fuentes de reputación.
5. **Detección de entidades sensibles:** identificar datos personales para su anonimización.
6. **Integración de resultados:** combinar las señales disponibles y devolver una evaluación de riesgo.

| Modalidad de entrada | Tratamiento propuesto |
|---|---|
| SMS, WhatsApp y notificaciones | Clasificación directa del texto |
| Email | Clasificación del cuerpo y análisis de metadatos |
| URL | Análisis independiente de enlaces |
| Imagen o captura de pantalla | OCR y posterior clasificación del texto |
| Audio o nota de voz | Transcripción y posterior clasificación |
| Vídeo | Extracción de audio y fotogramas relevantes |
| PDF y documentos | Extracción de texto y posterior clasificación |
| Número de teléfono | Análisis de reputación y señales disponibles |

**Importante:** el análisis de una llamada telefónica en tiempo real no debe darse por implementado únicamente por disponer de un clasificador de texto. La transcripción y análisis de audio requieren un flujo específico y deben ajustarse a las capacidades reales de la aplicación.

## 5. Estrategia de preparación de datos

Antes de entrenar el modelo será necesario realizar las siguientes tareas:

### 5.1. Auditoría inicial
- Comprobar el número de registros.
- Revisar columnas y tipos de datos.
- Identificar valores nulos.
- Analizar la distribución de etiquetas.
- Detectar duplicados exactos y aproximados.
- Identificar registros sin contenido útil.

### 5.2. Normalización
- Unificar nombres de columnas.
- Normalizar espacios y caracteres.
- Mantener el contenido original cuando sea necesario para auditoría.
- Crear una columna normalizada para el entrenamiento.
- Registrar la fuente de cada registro.

### 5.3. Normalización de etiquetas

No debemos convertir automáticamente todas las etiquetas en una única categoría de amenaza.

Propuesta inicial de taxonomía:

| Categoría original | Categoría normalizada |
|---|---|
| ham / legitimate / no spam | `legitimate` |
| spam | `spam` |
| phishing | `phishing` |
| smishing | `smishing` |
| scam / fraud | `scam` |
| unknown / sin etiqueta clara | `unknown` |

La categoría `unknown` no debe utilizarse como si fuera una etiqueta negativa. Los registros sin una clasificación fiable deben quedar fuera del entrenamiento supervisado hasta ser revisados.

### 5.4. División de datos

Para evaluar correctamente el modelo:
- Separar entrenamiento, validación y test.
- Evitar que mensajes duplicados aparezcan en conjuntos diferentes.
- Utilizar división estratificada cuando sea apropiado.
- Evitar fugas de información entre fuentes y particiones.
- Mantener un conjunto de test independiente para la evaluación final.

## 6. Evaluación del modelo

La exactitud (*accuracy*) no será suficiente para evaluar Avizor.

Debemos prestar especial atención a:

- **Precision:** qué proporción de los mensajes señalados como amenaza son realmente amenazas.
- **Recall:** qué proporción de las amenazas reales consigue detectar el modelo.
- **F1-score:** equilibrio entre precision y recall.
- **False Positive Rate:** proporción de mensajes legítimos marcados incorrectamente.
- **Confusion Matrix:** distribución de aciertos y errores por clase.

En Avizor, los falsos positivos son especialmente importantes: una aplicación que marque constantemente mensajes legítimos como peligrosos puede generar desconfianza y confusión en sus usuarios.

Por otro lado, los falsos negativos también son críticos, porque representan amenazas que el sistema no consigue detectar.

Se deberá evaluar el comportamiento del modelo por categoría de amenaza y no únicamente mediante una puntuación global.

## 7. Anonimización y NER

La anonimización debe tratarse como un componente independiente del clasificador.

Se propone investigar el reconocimiento de entidades nombradas (NER) para detectar:
- Nombres de personas.
- Direcciones.
- Correos electrónicos.
- Números de teléfono.
- Documentos de identidad.
- IBAN y datos financieros.
- Otros datos personales.

El objetivo es reducir la exposición de información personal durante el procesamiento y almacenamiento de mensajes.

La anonimización no debe destruir las señales necesarias para detectar amenazas. Por ejemplo, puede ser importante conservar que un mensaje solicita introducir un número de cuenta, aunque se elimine el número concreto.

También será necesario probar el sistema con datos sintéticos y ejemplos controlados para comprobar que no deja información sensible sin detectar.

## 8. Decisiones iniciales

A partir de la investigación realizada:

1. Utilizar SpaPhish como candidato principal para experimentar con phishing en español.
2. Auditar SpamSpa antes de incorporarlo, especialmente por su procedencia y posibles duplicados.
3. Utilizar UCI SMS Spam Collection como referencia complementaria para clasificación de spam en inglés.
4. Mantener PhishBench-External como candidato para el análisis específico de URLs.
5. No utilizar Sting9 en el entrenamiento hasta aclarar la contradicción de licencia.
6. Mantener separadas las etiquetas de spam, phishing, smishing y fraude.
7. Desarrollar primero un baseline de clasificación de texto antes de abordar modelos más complejos.

## 9. Próximos pasos

- [ ] Descargar SpaPhish versión 5.
- [ ] Descargar SpamSpa.
- [ ] Descargar UCI SMS Spam Collection.
- [ ] Revisar estructura, columnas y etiquetas de cada dataset.
- [ ] Calcular estadísticas y detectar duplicados.
- [ ] Documentar las fuentes y licencias.
- [ ] Preparar un dataset inicial normalizado.
- [ ] Entrenar un primer baseline con TF-IDF y un clasificador de Scikit-learn.
- [ ] Evaluar precision, recall, F1 y falsos positivos.
- [ ] Investigar modelos NER para anonimización.
- [ ] Preparar resultados y documentación para la integración con backend.

---

## 10. Fuentes consultadas

1. SpaPhish, versión 5. Mendeley Data. https://doi.org/10.17632/hz2d6gz7pc.5
2. SpamSpa. Hugging Face Datasets. https://huggingface.co/datasets/Gabrielaz/spamspa
3. SMS Spam Collection. UCI Machine Learning Repository. https://doi.org/10.24432/C5CC84
4. Sting9 Dataset. https://sting9.org/dataset
5. Sting9 License. https://sting9.org/license
6. PhishBench-External. Mendeley Data. https://data.mendeley.com/datasets/2ctjcnm9kn

**Nota metodológica:** esta investigación es una revisión inicial de las fichas y documentación pública de los datasets. Las cantidades, etiquetas, licencias y estructuras deberán volver a comprobarse sobre los ficheros descargados antes de utilizarlos en entrenamiento o distribución. La disponibilidad pública de un dataset no garantiza por sí sola que sea adecuado para un producto comercial.
