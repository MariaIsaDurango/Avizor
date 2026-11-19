Investigación y comparación de datasets para Avizor
Estado: Investigación inicial y auditoría de calidad completada para SpaPhish y SpamSpa.
Objetivo: Identificar fuentes de datos adecuadas para desarrollar y evaluar los sistemas de detección de amenazas digitales de Avizor.
1. Objetivo de la investigación
Avizor pretende ayudar a personas mayores a identificar posibles amenazas digitales. Estas amenazas pueden llegar a través de SMS, notificaciones, aplicaciones de mensajería, correos electrónicos, enlaces, imágenes, documentos y comunicaciones telefónicas.

Por este motivo, la investigación no debe limitarse a encontrar un único dataset. Es necesario estudiar diferentes fuentes de datos y determinar qué tipo de amenaza y modalidad cubre cada una.

Los objetivos iniciales son:
- Identificar datasets públicos relevantes.
- Comparar idioma, formato, etiquetas, tamaño y licencia.
- Evaluar su utilidad para el proyecto.
- Detectar limitaciones y posibles problemas de calidad.
- Seleccionar fuentes para preparar un primer conjunto de entrenamiento y evaluación.
- Definir una estrategia de clasificación que permita incorporar diferentes modalidades.
2. Comparativa inicial de datasets
2.1. SpamSpa
Fuente: Hugging Face – SpamSpa
Característica	Información
Tipo	Mensajes de spam y no spam
Idioma	Español
Formato	CSV
Variables principales	text, label
Etiquetas observadas	0 = no spam; 1 = spam
Licencia declarada	Apache 2.0
Modalidad	Texto


Descripción

SpamSpa es un conjunto de mensajes en español etiquetados como spam o no spam. Está orientado a tareas de clasificación binaria de texto.

La ficha del dataset indica que sus fuentes incluyen SMS Spam Collection Dataset y SMS Validation Dataset.

Ventajas
- Está en español.
- Tiene una estructura sencilla.
- Puede servir para desarrollar un clasificador de mensajes.
- La ficha declara licencia Apache 2.0.
Limitaciones
- No debemos asumir que todos los mensajes representan intentos de phishing o fraude: spam y phishing no son exactamente lo mismo.
- Es necesario revisar la procedencia y las condiciones de reutilización de los datos originales.
- Presenta desequilibrio entre clases.
- Se han detectado duplicados y solapamiento entre entrenamiento y test.
Valoración inicial: candidato para ampliar el entrenamiento de clasificación de spam en español, pendiente de verificar la procedencia y resolver los problemas de calidad detectados.
2.2. SpaPhish
Fuente: Mendeley Data – SpaPhish, versión 5
DOI: 10.17632/hz2d6gz7pc.5
Característica	Información
Tipo	Correos electrónicos legítimos y phishing
Idioma	Español
Registros	1.395
Phishing	731
Legítimos	664
Variables	47
Licencia declarada	CC BY 4.0
Modalidad	Texto y metadatos de correo


Descripción

SpaPhish es un corpus de correos electrónicos en español recopilados de buzones personales e institucionales de los autores. Los mensajes abarcan el periodo 2014–2025 y, según la documentación del dataset, han sido anonimizados.

Incluye:
- Asunto y cuerpo del correo.
- Etiqueta binaria de clasificación.
- Información técnica derivada, como URLs, número de enlaces y adjuntos.
- Anotaciones sobre técnicas de persuasión e ingeniería social.
Las anotaciones psicológicas contemplan cinco dimensiones: autoridad, prueba social, simpatía/similitud y engaño, compromiso/integridad/reciprocidad y distracción.

Ventajas
- Es una fuente directamente relacionada con el phishing.
- Los mensajes están escritos originalmente en español.
- Incluye ejemplos legítimos y maliciosos.
- Permite investigar señales lingüísticas y técnicas.
- Las anotaciones de ingeniería social pueden ayudar a estudiar cómo se construyen los mensajes fraudulentos.
Limitaciones
- Está centrado en correo electrónico, no en SMS, llamadas o mensajes de WhatsApp.
- Su tamaño es relativamente reducido para entrenar modelos complejos desde cero.
- No representa necesariamente los mensajes fraudulentos dirigidos específicamente a personas mayores.
- Será necesario revisar el significado exacto de las etiquetas y las columnas antes de incorporarlo al entrenamiento.
Valoración inicial: candidato prioritario para el primer clasificador de phishing en español.
2.3. UCI SMS Spam Collection
Fuente: UCI Machine Learning Repository – SMS Spam Collection
DOI: 10.24432/C5CC84
Característica	Información
Tipo	SMS legítimos y spam
Idioma	Principalmente inglés
Registros	5.574
Licencia declarada	CC BY 4.0
Etiquetas	ham y spam
Modalidad	Texto


Descripción

Es un conjunto de mensajes SMS etiquetados como legítimos (ham) o spam. Se creó a partir de varias fuentes, entre ellas mensajes de spam recopilados de un foro británico y mensajes legítimos procedentes de corpus académicos.

Ventajas
- Es un dataset conocido y utilizado en investigación.
- Tiene más registros que SpaPhish.
- Puede servir como referencia para desarrollar y comparar modelos de clasificación.
- Su licencia permite compartir y adaptar los datos con atribución.
Limitaciones
- Está compuesto principalmente por mensajes en inglés.
- Parte de los mensajes procede de contextos y épocas anteriores a las amenazas actuales.
- La etiqueta spam no equivale necesariamente a phishing o fraude.
- No debe mezclarse directamente con datos en español sin estudiar antes las diferencias lingüísticas.
Valoración inicial: útil como conjunto complementario para experimentación y comparación, pero no como fuente principal del modelo en español.
2.4. Sting9
Fuentes:
- Sting9 – Dataset
- Sting9 – Licencia
- Sting9 – GitHub
Característica	Información
Tipo	Phishing, smishing y estafas
Canales declarados	Email, SMS, WhatsApp, Telegram, Signal y otros
Idiomas	Multilingüe, según los campos de la plataforma
Datos	Mensajes anonimizados y metadatos
Licencia	Información contradictoria: CC0 en una página y ODC-BY-NC en las condiciones y licencia


Descripción

Sting9 es una iniciativa que recopila mensajes sospechosos de diferentes canales digitales. Su esquema contempla campos como tipo de mensaje, contenido, nivel de amenaza, tipo de ataque e idioma detectado.

Ventajas
- Su planteamiento contempla diferentes canales de comunicación.
- Incluye categorías de ataques más específicas que una clasificación simple de spam/no spam.
- Puede aportar ejemplos de smishing y otras estafas.
Limitaciones
- Existe una contradicción entre la página del dataset, que indica CC0, y la página de licencia y condiciones, que establecen ODC-BY-NC.
- La licencia ODC-BY-NC restringe el uso comercial y el entrenamiento de modelos destinados a productos comerciales.
- Antes de utilizarlo hay que aclarar las condiciones aplicables a la descarga concreta y al uso previsto por Avizor.
- Es necesario comprobar el volumen real, la calidad de las etiquetas y la distribución por idioma y canal.
Valoración inicial: interesante para investigación, pero no se incorporará al entrenamiento hasta aclarar las condiciones de licencia.
2.5. PhishBench-External
Fuente: Mendeley Data – PhishBench-External
Característica	Información
Tipo	URLs de phishing y legítimas
Registros	1.000
URLs de phishing	500
URLs legítimas	500
Licencia declarada	CC BY 4.0
Modalidad	URLs


Descripción

Es un conjunto equilibrado de URLs recopiladas para validar sistemas de detección de phishing.

Ventajas
- Está específicamente orientado a la detección de enlaces maliciosos.
- Tiene una distribución equilibrada entre URLs de phishing y legítimas.
- Puede utilizarse para experimentar con características de URLs.
Limitaciones
- No contiene mensajes completos.
- No permite detectar por sí solo técnicas de manipulación lingüística.
- El conjunto es pequeño.
- Debe revisarse la fecha de recopilación y la disponibilidad actual de los dominios antes de interpretar los resultados.
Valoración inicial: candidato para un módulo independiente de análisis de URLs, no para el clasificador principal de mensajes.
3. Comparación y selección inicial
Dataset	Idioma	Amenaza principal	Modalidad	Decisión inicial
SpamSpa	Español	Spam	Texto	Evaluar e incorporar si supera la auditoría
SpaPhish	Español	Phishing	Email y metadatos	Prioritario
UCI SMS Spam	Inglés	Spam	SMS	Complementario
Sting9	Multilingüe	Phishing, smishing y estafas	Varios canales	Pendiente de licencia
PhishBench-External	No centrado en idioma	URLs de phishing	URL	Candidato para módulo separado


La selección no implica que todos los datasets deban combinarse. Sus etiquetas y objetivos son diferentes y será necesario normalizarlos cuidadosamente.
4. Propuesta de arquitectura de análisis multimodal
El hecho de que Avizor deba analizar diferentes tipos de contenido no significa que sea necesario entrenar un modelo distinto para cada formato.

Se propone una arquitectura por etapas:
1. Recepción del contenido: texto, SMS, notificaciones, correo, imagen, audio, vídeo, documento o URL.
2. Extracción y normalización: convertir el contenido a formatos analizables.
3. Clasificación del texto: analizar mensajes y textos extraídos.
4. Análisis de URLs: evaluar enlaces mediante características y fuentes de reputación.
5. Detección de entidades sensibles: identificar datos personales para su anonimización.
6. Integración de resultados: combinar las señales disponibles y devolver una evaluación de riesgo.
Modalidad de entrada	Tratamiento propuesto
SMS, WhatsApp y notificaciones	Clasificación directa del texto
Email	Clasificación del cuerpo y análisis de metadatos
URL	Análisis independiente de enlaces
Imagen o captura de pantalla	OCR y posterior clasificación del texto
Audio o nota de voz	Transcripción y posterior clasificación
Vídeo	Extracción de audio y fotogramas relevantes
PDF y documentos	Extracción de texto y posterior clasificación
Número de teléfono	Análisis de reputación y señales disponibles


Importante: el análisis de una llamada telefónica en tiempo real no debe darse por implementado únicamente por disponer de un clasificador de texto. La transcripción y análisis de audio requieren un flujo específico y deben ajustarse a las capacidades reales de la aplicación.
5. Estrategia de preparación de datos
Antes de entrenar el modelo será necesario realizar las siguientes tareas.
5.1. Auditoría inicial
- Comprobar el número de registros.
- Revisar columnas y tipos de datos.
- Identificar valores nulos.
- Analizar la distribución de etiquetas.
- Detectar duplicados exactos y aproximados.
- Identificar registros sin contenido útil.
5.2. Normalización
- Unificar nombres de columnas.
- Normalizar espacios y caracteres.
- Mantener el contenido original cuando sea necesario para auditoría.
- Crear una columna normalizada para el entrenamiento.
- Registrar la fuente de cada registro.
5.3. Normalización de etiquetas
No debemos convertir automáticamente todas las etiquetas en una única categoría de amenaza.

Propuesta inicial de taxonomía:
Categoría original	Categoría normalizada
ham / legitimate / no spam	legitimate
spam	spam
phishing	phishing
smishing	smishing
scam / fraud	scam
unknown / sin etiqueta clara	unknown


La categoría unknown no debe utilizarse como si fuera una etiqueta negativa. Los registros sin una clasificación fiable deben quedar fuera del entrenamiento supervisado hasta ser revisados.
5.4. División de datos
Para evaluar correctamente el modelo:
- Separar entrenamiento, validación y test.
- Evitar que mensajes duplicados aparezcan en conjuntos diferentes.
- Utilizar división estratificada cuando sea apropiado.
- Evitar fugas de información entre fuentes y particiones.
- Mantener un conjunto de test independiente para la evaluación final.
6. Evaluación del modelo
La exactitud (accuracy) no será suficiente para evaluar Avizor.

Debemos prestar especial atención a:
- Precision: qué proporción de los mensajes señalados como amenaza son realmente amenazas.
- Recall: qué proporción de las amenazas reales consigue detectar el modelo.
- F1-score: equilibrio entre precision y recall.
- False Positive Rate: proporción de mensajes legítimos marcados incorrectamente.
- Confusion Matrix: distribución de aciertos y errores por clase.
En Avizor, los falsos positivos son especialmente importantes: una aplicación que marque constantemente mensajes legítimos como peligrosos puede generar desconfianza y confusión en sus usuarios.

Por otro lado, los falsos negativos también son críticos, porque representan amenazas que el sistema no consigue detectar.

Se deberá evaluar el comportamiento del modelo por categoría de amenaza y no únicamente mediante una puntuación global.
7. Anonimización y NER
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
8. Decisiones iniciales
A partir de la investigación y de la auditoría realizada:
1. Utilizar SpaPhish como candidato principal para experimentar con phishing en español.
2. No combinar directamente SpaPhish y SpamSpa, porque sus etiquetas representan problemas diferentes.
3. Evaluar SpamSpa como fuente complementaria para clasificación de spam, teniendo en cuenta sus duplicados y el solapamiento entre particiones.
4. Utilizar UCI SMS Spam Collection como referencia complementaria para clasificación de spam en inglés.
5. Mantener PhishBench-External como candidato para el análisis específico de URLs.
6. No utilizar Sting9 en el entrenamiento hasta aclarar la contradicción de licencia.
7. Mantener separadas las etiquetas de spam, phishing, smishing y fraude.
8. Desarrollar primero un baseline de clasificación de texto antes de abordar modelos más complejos.
9. Resultados de la auditoría de los datasets
Se ha realizado una auditoría exploratoria de SpaPhish y SpamSpa para comprobar sus dimensiones, estructura, distribución de etiquetas, valores ausentes, duplicados y consistencia de las particiones disponibles.

Los resultados corresponden a los archivos descargados y analizados durante esta fase.
9.1. SpaPhish
Dimensiones: 1.395 registros y 47 columnas.

Distribución de etiquetas:
Etiqueta	Interpretación observada	Registros	Porcentaje
0	Legítimo	664	47,6 %
1	Phishing	731	52,4 %
Total		1.395	100 %


La distribución está relativamente equilibrada, lo que facilita el desarrollo de un primer clasificador binario. La interpretación de las etiquetas debe mantenerse vinculada a la documentación original del dataset.

Valores ausentes

Se identificaron los siguientes valores ausentes:
Columna	Valores ausentes
attachments_types	1.124
attachments_sizes	1.124
urls	195
date	24
justif_distraction_A	5
subject	3
justif_distraction_B	3


Los valores ausentes de attachments_types y attachments_sizes son coherentes con mensajes que no contienen archivos adjuntos. Del mismo modo, los valores ausentes de urls observados corresponden a registros sin URLs.

Duplicados y consistencia
- No se encontraron filas duplicadas completas.
- No se encontraron hashes repetidos.
- No se detectaron asuntos ausentes en más de tres registros.
- Todos los registros tienen cuerpo de mensaje.
- Se comprobó la coherencia entre la presencia de información en urls y el valor de url_count.
La comprobación realizada sobre las URLs fue de presencia y ausencia: los registros con url_count = 0 no contienen información en urls, mientras que los registros con url_count > 0 sí contienen información. Esta comprobación no valida que el número exacto de URLs almacenadas coincida con el valor de url_count. Esa validación más detallada queda pendiente.

Longitud de los mensajes

Se observaron diferencias descriptivas en la longitud del asunto y el cuerpo combinados:
Clase	Longitud media	Longitud mediana
Legítimos	1.801,9 caracteres	1.144
Phishing	758,2 caracteres	617


Estas diferencias describen únicamente los registros analizados. No deben interpretarse como una regla general para detectar phishing ni como una característica suficiente para clasificar mensajes.
9.2. SpamSpa
SpamSpa se distribuye en dos archivos independientes:
Partición	Registros	Columnas
Train	4.457	2
Test	1.115	2
Total	5.572	2


Las columnas disponibles son text y label.

Distribución de etiquetas
Partición	Etiqueta 0	Etiqueta 1
Train	3.859	598
Test	966	149


La distribución es aproximadamente del 86,6 % para la clase 0 y del 13,4 % para la clase 1.

La inspección exploratoria de ejemplos sugiere que la etiqueta 0 corresponde a mensajes normales (ham) y la etiqueta 1 a spam. Esta interpretación debe contrastarse con la documentación original antes de consolidarla como definición definitiva.

Valores ausentes y duplicados
Comprobación	Train	Test
Valores ausentes en text	2	0
Filas duplicadas exactas	275	25


Los duplicados representan aproximadamente el 6,17 % de los registros de entrenamiento y el 2,24 % de los registros de test.

Solapamiento entre train y test

Se detectaron 118 textos presentes en ambas particiones, considerando los textos normalizados mediante eliminación de espacios exteriores y conversión a minúsculas.

Esto representa aproximadamente el 10,83 % de los textos distintos del conjunto de test.

Este solapamiento puede producir una evaluación demasiado optimista si se utiliza directamente la separación original. Antes de entrenar y evaluar un modelo será necesario estudiar los duplicados y establecer una división que evite la fuga de información entre conjuntos.
9.3. Comparación de calidad de los datos
Criterio	SpaPhish	SpamSpa
Dimensiones	1.395 × 47	Train: 4.457 × 2; test: 1.115 × 2
Distribución	Relativamente equilibrada	Desequilibrada
Duplicados completos	0	275 train y 25 test
Valores ausentes	Varias columnas con ausencias	2 textos vacíos en train
Solapamiento entre particiones	No aplica	118 textos compartidos
Uso recomendado	Primer clasificador de phishing	Clasificador complementario de spam


9.4. Decisiones derivadas de la auditoría
Los resultados refuerzan la decisión de utilizar SpaPhish como primera fuente para desarrollar el clasificador de phishing en español.

SpamSpa puede aportar información útil para una clasificación complementaria de spam, pero no debe incorporarse directamente al mismo modelo como si sus etiquetas fueran equivalentes a las de SpaPhish.

Antes de utilizar SpamSpa será necesario:
- Revisar los duplicados exactos.
- Resolver el solapamiento entre train y test.
- Revisar los dos registros sin texto.
- Confirmar el significado de las etiquetas.
- Verificar la procedencia y las condiciones de reutilización.
Para SpaPhish será necesario:
- Confirmar el significado de las etiquetas con la documentación original.
- Mantener las ausencias estructurales de adjuntos y URLs correctamente interpretadas.
- Realizar una validación adicional del recuento exacto de URLs.
- Evitar que las anotaciones derivadas de la clasificación se utilicen como variables predictivas.
9.5. Trazabilidad y reproducibilidad
Para facilitar la reproducción de los resultados se deben registrar los siguientes datos:
Elemento	SpaPhish	SpamSpa
Fuente	Mendeley Data	Hugging Face
Versión declarada	Versión 5	Pendiente de concretar
Archivos utilizados	Spaphish dataset - DiB.csv	train.csv, test.csv
Fecha de descarga	No registrada	No registrada
SHA256	656B2245D58DA72D640680E5C2A168673A130B38607F2A427C773BBB167E995E	Train: 207FF503074707CAA063AD066D8CCEF3DA79D2DB9C83F586B01F2F4D5221E2DE
Test: BB43E281EACA4F25936F628C436450E201ABC65E7B7B02CCC6922B91BF0D5E48
Licencia declarada	CC BY 4.0	Apache 2.0, pendiente de revisar las fuentes originales


Los hashes SHA256 se han calculado sobre los tres archivos originales analizados mediante PowerShell (Get-FileHash -Algorithm SHA256). Las fechas de descarga exactas no están registradas. Las fechas de última modificación observadas en el equipo local (17/11/2026) no se consideran fechas de descarga y, por tanto, no se utilizan como sustituto.

Ubicación local de los archivos:
ml/
└── data/
    └── raw/
        ├── spaphish/
        │   └── Spaphish dataset - DiB.csv
        └── spamspa/
            ├── train.csv
            └── test.csv
Los archivos originales se mantienen separados del código y de la documentación del análisis. No deben incluirse en el repositorio sin revisar previamente sus condiciones de licencia y privacidad.
9.6. Validaciones realizadas y limitaciones
Durante esta fase se han realizado comprobaciones exploratorias y manuales sobre los archivos descargados:
- Lectura y comprobación de dimensiones.
- Inspección de columnas y tipos de datos.
- Revisión de valores ausentes.
- Cálculo de distribuciones de etiquetas.
- Detección de duplicados exactos.
- Comprobación del solapamiento entre particiones de SpamSpa.
- Comprobación de presencia y ausencia de URLs en SpaPhish.
- Revisión de la estructura y carga de los archivos desde el entorno local.
Estas comprobaciones se han realizado mediante notebooks de exploración y no constituyen todavía una suite de tests automatizados de calidad de datos.

La automatización de estas validaciones y la incorporación de tests específicos quedan para una siguiente fase del proyecto.
10. Próximos pasos
- [x] Descargar SpaPhish versión 5.
- [x] Descargar SpamSpa.
- [x] Revisar estructura, columnas y etiquetas de ambos datasets.
- [x] Calcular estadísticas y detectar duplicados.
- [x] Comprobar valores ausentes.
- [x] Analizar el solapamiento entre train y test de SpamSpa.
- [x] Documentar los resultados iniciales de la auditoría.
- [x] Calcular y registrar los hashes SHA256 de los archivos originales.
- [ ] Registrar las fechas exactas de descarga y confirmar la versión de SpamSpa.
- [ ] Verificar la procedencia y condiciones de reutilización de SpamSpa.
- [ ] Completar la validación exacta del recuento de URLs en SpaPhish.
- [ ] Preparar un dataset inicial normalizado.
- [ ] Entrenar un primer baseline con TF-IDF y un clasificador de Scikit-learn.
- [ ] Evaluar precision, recall, F1 y falsos positivos.
- [ ] Investigar modelos NER para anonimización.
- [ ] Preparar resultados y documentación para la integración con backend.
11. Fuentes consultadas
1. SpaPhish, versión 5. Mendeley Data. https://doi.org/10.17632/hz2d6gz7pc.5
2. SpamSpa. Hugging Face Datasets. https://huggingface.co/datasets/Gabrielaz/spamspa
3. SMS Spam Collection. UCI Machine Learning Repository. https://doi.org/10.24432/C5CC84
4. Sting9 Dataset. https://sting9.org/dataset
5. Sting9 License. https://sting9.org/license
6. PhishBench-External. Mendeley Data. https://data.mendeley.com/datasets/2ctjcnm9kn
Nota metodológica: esta investigación combina una revisión inicial de las fichas y documentación pública con una auditoría exploratoria de los archivos descargados de SpaPhish y SpamSpa. Las cantidades y características recogidas en la auditoría corresponden a los archivos analizados. Las licencias, procedencia y condiciones de reutilización deberán verificarse antes de incorporar los datos a un producto o distribuirlos. La disponibilidad pública de un dataset no garantiza por sí sola que sea adecuado para un producto comercial.

## 9.7. Instrucciones para reproducir la descarga y la auditoría

1. Descargar **SpaPhish, versión 5**, desde [Mendeley Data](https://data.mendeley.com/datasets/hz2d6gz7pc/5). Guardar el archivo `Spaphish dataset - DiB.csv` en `ml/data/raw/spaphish/`.
2. Descargar los archivos `train.csv` y `test.csv` de [SpamSpa en Hugging Face](https://huggingface.co/datasets/Gabrielaz/spamspa). Guardarlos en `ml/data/raw/spamspa/`. La versión o revisión exacta de SpamSpa utilizada todavía debe confirmarse.
3. Mantener los CSV originales fuera del repositorio y comprobar que las carpetas de datos están excluidas mediante `.gitignore`.
4. Desde la raíz del repositorio, ejecutar la auditoría con:

   ```bash
   python ml/src/audit_datasets.py
   ```

5. Comparar los hashes SHA256 de los archivos descargados con los valores de la sección 9.5. Si no coinciden, registrar la nueva versión/descarga y volver a generar las estadísticas antes de comparar resultados.

**Limitación de trazabilidad:** no se registraron las fechas exactas de descarga y no se ha identificado una revisión inmutable concreta de SpamSpa. Por tanto, los hashes permiten identificar los archivos analizados, pero no sustituyen la confirmación de la versión y procedencia.
