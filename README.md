<div align="center">

<img src="mobile/assets/logo-web.png" alt="Avizor" width="180"/>

<h1>Avizor</h1>

<p>Aplicación Android que protege a personas mayores frente a estafas digitales.<br/>
El mayor comparte un mensaje, enlace, llamada o archivo; Avizor responde con un semáforo<br/>
<strong>verde · ámbar · rojo</strong> y consejos concretos sobre qué hacer.</p>

<a href="https://avizor-production.up.railway.app">
  <img src="https://img.shields.io/badge/Ver%20en%20vivo-164E55?style=for-the-badge&logo=railway&logoColor=white" alt="Ver en vivo"/>
</a>

<br/><br/>

<!-- App móvil -->
<img src="https://img.shields.io/badge/React_Native-20232A?style=flat-square&logo=react&logoColor=61DAFB" alt="React Native"/>
<img src="https://img.shields.io/badge/Expo_SDK_52-1C1E24?style=flat-square&logo=expo&logoColor=white" alt="Expo"/>
<img src="https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript"/>
&nbsp;
<!-- Backend -->
<img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
<img src="https://img.shields.io/badge/Python_3.11-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
<img src="https://img.shields.io/badge/PostgreSQL_16-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
<img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
&nbsp;
<!-- IA / ML -->
<img src="https://img.shields.io/badge/BETO_ONNX-164E55?style=flat-square&logoColor=white" alt="BETO ONNX"/>
<img src="https://img.shields.io/badge/spaCy-09A3D5?style=flat-square&logo=spacy&logoColor=white" alt="spaCy"/>
<img src="https://img.shields.io/badge/Tesseract_OCR-F4B19B?style=flat-square&logoColor=164E55" alt="Tesseract"/>
<img src="https://img.shields.io/badge/Groq-F55036?style=flat-square&logoColor=white" alt="Groq"/>
<img src="https://img.shields.io/badge/ChromaDB-164E55?style=flat-square&logoColor=white" alt="ChromaDB"/>
&nbsp;
<!-- Infra -->
<img src="https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white" alt="Railway"/>
<img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white" alt="GitHub Actions"/>

<br/>

</div>

---

## ¿Qué es Avizor?

Las personas mayores reciben cada día mensajes de texto, correos, llamadas y notificaciones que pueden ser intentos de estafa. Detectarlos requiere experiencia digital que muchos no tienen, y los estafadores lo saben: el 70 % de las víctimas de phishing y vishing en España tienen más de 60 años.

Avizor actúa como un guardián silencioso en el teléfono del mayor. Intercepta automáticamente las notificaciones sospechosas, o el propio mayor puede reenviar cualquier mensaje dudoso directamente desde WhatsApp, SMS u otras apps. En segundos, Avizor analiza el contenido y responde con un resultado claro:

- 🟢 **Verde — seguro.** La app no hace nada más.
- 🟡 **Ámbar — sospechoso.** Se bloquea en silencio y se avisa al familiar.
- 🔴 **Rojo — peligroso.** Pantalla de bloqueo con instrucciones concretas: qué hacer, a quién llamar, cómo denunciarlo.

El sistema está diseñado para que el mayor no necesite entender cómo funciona la tecnología. No hay puntuaciones, no hay tecnicismos, no hay decisiones que tomar. Si algo es peligroso, la app lo para y explica qué hacer en lenguaje sencillo.

---

## Cómo funciona

```
 Sénior comparte un mensaje, enlace, llamada o imagen
                        │
                        ▼
         Anonimización en el dispositivo          ← datos personales sustituidos
         [NAME] [IBAN] [PHONE] [EMAIL]…               por etiquetas, nunca salen en claro
                        │
                        ▼
              POST /api/v1/analyses
                        │
              ┌─────────┴──────────┐
              │  Vía rápida <800ms │   texto, URL, teléfono
              │  Clasificador BETO │
              │  + reputación      │
              └─────────┬──────────┘
                        │
              ┌─────────┴──────────┐
              │  Vía manual <15s   │   imágenes, PDFs, audio
              │  OCR (Tesseract)   │
              │  + Agente RAG      │   fuentes: INCIBE, OSI, Banco de España
              │    (Groq)          │
              └─────────┬──────────┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
         GREEN         AMBER         RED
         allow     silent_block   block_and_alert
                    aviso push    pantalla de bloqueo
                    al tutor      + push al tutor
```

La IA nunca escribe texto libre al sénior. Selecciona una plantilla revisada (`DANGEROUS_LINK`, `FAKE_DO_NOT_TOUCH`, `SUSPICIOUS_CALL`…) y el sénior ve siempre instrucciones claras y probadas.

---

## Modos de uso

Avizor tiene tres perfiles distintos según la situación del mayor:

| Perfil | Quién es | Qué puede hacer |
|---|---|---|
| **Sénior vinculado** | Mayor con un familiar que lo supervisa | Recibe protección automática; su familiar configura todo |
| **Sénior autónomo** | Mayor sin tutor disponible | Se registra solo; ve su propio historial; gestiona su cuenta |
| **Tutor** | Familiar o cuidador | Recibe alertas push; revisa el historial; aprueba o rechaza desbloqueos |

**Vinculación tutor ↔ sénior:** el tutor genera un código de 6 dígitos desde su app. El sénior lo introduce en la suya. Listo: el tutor ya recibe las alertas y puede configurar el perfil de accesibilidad del mayor (tamaño de letra, daltonismo, hipoacusia) sin que el sénior tenga que tocar nada.

---

## Privacidad por diseño

La privacidad no es una opción en Avizor: es una restricción técnica que el sistema impone activamente.

- **El texto se anonimiza antes de salir del dispositivo.** Nombres, DNI, IBAN, tarjetas, emails y teléfonos se sustituyen por etiquetas antes de enviarse al servidor. Si el backend recibe texto sin anonimizar, rechaza la petición (`422 CONTENT_NOT_ANONYMIZED`).
- **Los archivos nunca se guardan.** Las imágenes, PDFs y audios se procesan en memoria del servidor y se descartan al terminar. Nunca se escriben en disco ni en base de datos.
- **El texto temporal se borra automáticamente.** Verde: mismo día. Ámbar: 7 días. Rojo: 30 días.
- **Los teléfonos se guardan solo como hash.** El número de un remitente se almacena con HMAC-SHA256; el valor real nunca sale del dispositivo.
- **Los nombres en PDFs e imágenes también se tapan.** El servidor usa spaCy (`es_core_news_md`) para detectar y reemplazar nombres de personas antes de que el texto llegue al clasificador o al agente.

---

## Accesibilidad

Cada decisión de diseño parte de que el usuario del teléfono puede tener baja visión, daltonismo, hipoacusia o no estar familiarizado con la tecnología.

**El tutor configura el perfil de accesibilidad del sénior** al crear la vinculación. El sénior no configura nada.

| Condición | Qué cambia |
|---|---|
| Baja visión o ceguera | Texto más grande en toda la app |
| Daltonismo | El semáforo lleva etiqueta de texto: SEGURO / SOSPECHOSO / PELIGRO |
| Hipoacusia | Alertas visuales más prominentes |

La app detecta automáticamente si TalkBack (lector de pantalla Android) está activo. Todos los botones tienen etiqueta en español claro, los formularios expandibles anuncian su estado y los mensajes de error se leen en voz alta en cuanto aparecen (`accessibilityLiveRegion="assertive"`).

**En el portal web** (usado por tutores): fuente sin serifa con interlineado amplio, modo sepia automático en modo oscuro para reducir el efecto de vibración visual, animaciones desactivadas si el sistema operativo lo indica (`prefers-reduced-motion`), y navegación completa por teclado con foco visible.

<details>
<summary><strong>Ver todas las decisiones de accesibilidad (ADR 0002)</strong></summary>

- Sin emojis como metáforas: se usan iconos Lucide con etiqueta de texto junto a ellos.
- Modo sepia automático en modo oscuro (fondo crema `#f5f0e8` en lugar de negro puro).
- `prefers-reduced-motion`: todas las animaciones desaparecen si el SO lo indica.
- `scroll-behavior: smooth` solo si `prefers-reduced-motion: no-preference`.
- Foco visible (`:focus-visible`) en todos los elementos interactivos para navegación por teclado.
- Toggle de contraseña visible en todos los campos (útil para personas con dislexia).
- `aria-live="polite"` en errores de formulario, código de vinculación, cuenta atrás y contadores del panel.
- Labels siempre visibles encima del campo; ningún input depende solo del placeholder.
- Formularios con un campo por línea y espaciado generoso.
- Contenedores de gráficas con `min-height` en vez de `height` fija (el texto grande del navegador no recorta el contenido).
- HTML semántico: `<nav>`, `<main>`, `<section>`, `role="tablist"`, `role="tab"`, `role="tabpanel"`.
- Separación de contenido público y autenticado: la landing no muestra datos privados a usuarios sin sesión.

Pendiente de testing con NVDA (lector de pantalla Windows). Checklist completo en [`docs/decisions/0002-accesibilidad-web.md`](docs/decisions/0002-accesibilidad-web.md).

</details>

---

## Decisiones de diseño

Las más importantes del proyecto — qué decidimos, por qué y qué cambió en la app.

**El LLM nunca escribe texto libre al sénior.** Cuando algo es peligroso, la app muestra una plantilla predefinida y revisada (`DANGEROUS_LINK`, `FAKE_DO_NOT_TOUCH`, `SUSPICIOUS_CALL`, `ASKS_BANK_DETAILS`, `LOOKS_SAFE`, `UNSURE_CALL_FAMILY`). La IA solo elige cuál mostrar. Un modelo de lenguaje puede alucinar o generar texto confuso; para una persona mayor en situación de alarma, eso es inaceptable.

**Solo Android para el sénior automático.** iOS no permite a apps de terceros leer notificaciones de otras apps ni interceptar llamadas. Es una restricción del sistema operativo de Apple, no algo que podamos resolver con código. Los tutores pueden usar cualquier plataforma.

**Sénior autónomo (`senior_solo`).** No todo el mundo tiene un familiar con tiempo y conocimientos para hacer de tutor. Este rol permite que el mayor se registre solo, vea su historial y gestione su cuenta. No puede desbloquear contenido bloqueado en el MVP: si un estafador le llama y le presiona para que lo haga, la app no se lo permite.

**React Native con Expo en lugar de Flutter.** El equipo domina TypeScript y el panel web ya estaba en ese lenguaje. Flutter requeriría aprender Dart desde cero. La consecuencia: la carpeta `android/` está commiteada en el repositorio y cualquier cambio nativo hay que hacerlo directamente en `AndroidManifest.xml` y en los ficheros Kotlin.

<details>
<summary><strong>Ver todas las decisiones (ADRs 0001–0009)</strong></summary>

**Navegación: React Navigation sobre Expo Router (ADR 0001)**
Expo Router está pensado para apps con rutas parecidas a las de una web. Avizor tiene un árbol condicionado por rol (sénior / tutor / sénior autónomo) que se controla mejor de forma explícita. Las rutas están en [`mobile/src/navigation/`](mobile/src/navigation/).

**OCR con Tesseract en servidor (ADR 0007)**
Se evaluaron ML Kit en el móvil (aumenta la APK, más trabajo), un modelo de visión de Groq (enviaría la imagen sin anonimizar a un tercero) y Tesseract local. Tesseract gana: local, sin dependencias externas, calidad suficiente para capturas en español. Las imágenes sin texto legible salen como ámbar (`UNSURE_CALL_FAMILY`), no como "seguro". Límite: 8 s y 5000 caracteres por imagen.

**Nombres tapados con spaCy md (ADR 0009)**
`regex-v0` no detecta nombres propios. Se evaluaron `es_core_news_sm` (~160 MB, confundía "Mamá" o "Receta" con nombres) y `es_core_news_md` (~350 MB, resuelve esos casos). Se eligió `md`. Carga perezosa: no gasta RAM si nadie envía archivos. Limitación conocida: datos médicos no se tapan.

**Esquema preparado para N tutores, MVP con 1 (ADR 0004)**
La tabla `pairings` admite varios tutores sin cambios de esquema. En el MVP solo hay uno. Requisito antes de activar varios: el consentimiento debe indicar a qué tutor específico autoriza el sénior, y hace falta un test de concurrencia en los desbloqueos.

**Umbral de 5 reportes para publicar indicadores (ADR 0005)**
Un dominio, URL o teléfono no aparece en el ranking público con menos de 5 reportes. Con 1 reporte ya sale ámbar en la detección; con 5, rojo y entra en el ranking. Los reportes manuales del sénior cuentan por dispositivo (no por repetición), primer paso hacia contar personas distintas.

**Borrado completo y físico de cuenta (ADR 0008)**
Al eliminar la cuenta se borra todo: usuario, dispositivos, análisis, consentimientos, alertas y desbloqueos. No es borrado lógico. Se conservan los indicadores agregados de reputación (no identifican a nadie). Se pide la contraseña antes de proceder: un móvil desbloqueado no es suficiente. Si un tutor se borra y su sénior se queda sin nadie, el sénior también se da de baja.

</details>

---

## Estructura del repositorio

```
mobile/     React Native + Expo (app Android)
backend/    FastAPI + PostgreSQL (API REST)
ml/         Clasificador BETO ONNX
rag/        RAG con Groq + ChromaDB
docs/       ADRs, contratos, arquitectura, despliegue
```

---

## Puesta en marcha local

<details>
<summary><strong>Requisitos previos</strong></summary>

- Python 3.11+
- Node.js 20+
- Docker Desktop (para la base de datos local)
- Android Studio o dispositivo físico con USB debugging
- Java 17 (para compilar la app nativa)

</details>

<details>
<summary><strong>Variables de entorno</strong></summary>

Copia `.env.example` a `.env`:

```bash
cp .env.example .env
```

Variables mínimas para desarrollo local:

| Variable | Descripción |
|---|---|
| `POSTGRES_USER / PASSWORD / DB` | Credenciales de la BD local |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `PHONE_HMAC_KEY` | `openssl rand -hex 32` |
| `MAIL_PROVIDER` | `log` (imprime en terminal, no envía) |
| `CLASSIFIER_PROVIDER` | `keywords` (sin modelo ML) o `ml` |
| `AVIZOR_NER_MODEL` | `es_core_news_md` / `es_core_news_sm` / vacío |

Las claves externas (`AVIZOR_VT_KEY`, `AVIZOR_GSB_KEY`, `GROQ_API_KEY`…) son opcionales en local.

</details>

<details>
<summary><strong>Base de datos, backend y app móvil</strong></summary>

```bash
# 1. Base de datos
docker compose up -d db
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

# 2. Backend
uvicorn app.main:app --reload
# → http://localhost:8000  |  Swagger: http://localhost:8000/docs

# 3. App móvil
cd mobile
npm install
npx expo start --android       # requiere emulador o dispositivo conectado
# npx expo run:android         # genera el APK de desarrollo
```

</details>

<details>
<summary><strong>RAG (opcional)</strong></summary>

Solo necesario si `AVIZOR_RAG_ENABLED=true`.

```bash
cd rag
pip install -r requirements.txt
# Rellena GROQ_API_KEY y CHROMA_PATH en .env
python ingest.py   # indexa el corpus (INCIBE, OSI, Banco de España)
```

</details>

---

## Base de datos

PostgreSQL 16 · 12 tablas · PKs en UUID · fechas en ISO 8601 UTC

| Grupo | Tablas |
|---|---|
| Usuarios y acceso | `users`, `devices` |
| Vinculación y consentimiento | `pairings`, `consents` |
| Análisis | `analyses`, `temp_content`, `analysis_attachments` |
| Alertas | `alerts`, `unlocks` |
| Reputación | `indicators`, `indicator_reports`, `cases` |

<details>
<summary><strong>Usuarios y acceso</strong></summary>

**`users`** — Una fila por persona registrada.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador único |
| `role` | enum | `senior` · `guardian` (tutor) · `senior_solo` · `admin` |
| `display_name` | text | Nombre de pila (sin apellidos) |
| `email` | citext | Solo tutores y admins; único e insensible a mayúsculas |
| `password_hash` | text | bcrypt; `null` en séniors vinculados (sin cuenta propia) |
| `phone` | text | Teléfono del tutor (botón "Llamar a tu familiar") |
| `is_verified` | bool | El tutor ha confirmado su email |
| `token_version` | int | Sube al cambiar contraseña → invalida todas las sesiones abiertas |
| `accessibility_profile` | jsonb | Preferencias de tamaño de texto, contraste, etc. (solo sénior) |
| `deleted_at` | timestamptz | Borrado lógico; la fila se purga 30 días después |

**`devices`** — Un dispositivo Android por usuario.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | Identificador del dispositivo |
| `user_id` | UUID FK→users | Propietario |
| `platform` | text | `android` (iOS no soportado) |
| `push_token` | text | Token Expo para notificaciones push |
| `app_version` | text | Versión de la app instalada |
| `last_seen_at` | timestamptz | Última actividad |

</details>

<details>
<summary><strong>Vinculación y consentimiento</strong></summary>

**`pairings`** — El tutor genera un código de 6 dígitos; el sénior lo introduce para vincularse.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | — |
| `guardian_id` | UUID FK→users | Tutor que creó el código |
| `senior_id` | UUID FK→users | Sénior que lo canjeó (`null` hasta que se canjea) |
| `code` | char(6) | Código temporal |
| `senior_display_name` | text | Nombre que tecleó el tutor para su familiar |
| `guardian_phone` | text | Teléfono del tutor copiado al sénior al vincular |
| `senior_accessibility_profile` | jsonb | Perfil de accesibilidad elegido por el tutor |
| `expires_at` | timestamptz | El código caduca si no se canjea |
| `redeemed_at` | timestamptz | Momento en que el sénior lo introdujo |
| `active` | bool | `false` si se desvinculó |

**`consents`** — Registro legal del consentimiento de monitorización (RGPD).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | — |
| `senior_id` | UUID FK→users | Sénior cubierto |
| `type` | enum | `self` (el propio sénior) · `legal_guardianship` (tutor legal) |
| `scope` | array[channel] | Canales autorizados: `sms`, `call`, `notification`, `screen`, `manual` |
| `text_version` | text | Versión del texto legal aceptado |
| `granted_by` | UUID FK→users | Quien aceptó (el sénior o el tutor) |
| `evidence` | jsonb | Documento de tutela (obligatorio si `type = legal_guardianship`) |
| `granted_at` | timestamptz | Fecha de aceptación |
| `revoked_at` | timestamptz | Fecha de retirada (`null` si sigue activo) |

</details>

<details>
<summary><strong>Análisis de contenido</strong></summary>

**`analyses`** — Una fila por cada análisis. No almacena el texto original.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID PK | — |
| `device_id` | UUID FK→devices | Dispositivo que envió el análisis |
| `channel` | enum | `sms` · `call` · `notification` · `screen` · `manual` |
| `origin` | enum | `automatic` (interceptado) · `manual` (enviado a mano) |
| `input_types` | array[enum] | `text`, `image`, `audio`, `url`, `phone_number`, `document` |
| `sender_hash` | text | Remitente anonimizado con HMAC-SHA256 |
| `risk_level` | enum | Resultado: `green` · `amber` · `red` |
| `threat_type` | enum | `phishing`, `smishing`, `vishing`, `spam`, `bank_fraud`, `identity_theft`, `other`, `none` |
| `action` | enum | `allow` · `silent_block` · `block_and_alert` |
| `block_template` | text | Plantilla de pantalla de bloqueo mostrada |
| `confidence` | numeric(4,3) | Confianza del clasificador (0–1) |
| `phase` | enum | `fast` (clasificador BETO) · `agent` (enriquecido por RAG) |
| `latency_ms` | int | Tiempo de respuesta del servidor |

**`temp_content`** — Texto anonimizado; se borra automáticamente. Verde: mismo día · Ámbar: 7 d · Rojo: 30 d.

**`analysis_attachments`** — Solo metadatos. El archivo original nunca se guarda en servidor.

</details>

<details>
<summary><strong>Alertas y desbloqueos</strong></summary>

**`alerts`** — Notificación al tutor cuando hay contenido ámbar o rojo. Estados: `new` · `seen` · `confirmed_fraud` · `false_positive`.

**`unlocks`** — Cuando el sénior pide al tutor que levante un bloqueo. El tutor tiene un tiempo límite para responder. Estados: `pending_guardian` · `approved` · `rejected` · `expired`.

</details>

<details>
<summary><strong>Indicadores de reputación y casos</strong></summary>

**`indicators`** — Dominios, URLs y teléfonos sospechosos recopilados por los reportes. Los teléfonos se guardan solo como hash (nunca en claro). Se publican en el ranking solo con ≥ 5 reportes.

**`indicator_reports`** — Qué dispositivo reportó qué indicador. Un dispositivo cuenta una sola vez por indicador.

**`cases`** — Casos que abren los administradores para investigar indicadores o análisis. Estados: `open` · `in_review` · `closed`.

</details>

---

## Equipo

| Nombre | GitHub |
|---|---|
| Mariajosé Alvarez | [@MajoRodri](https://github.com/MajoRodri) |
| Maria Isabel Durango | [@MariaIsaDurango](https://github.com/MariaIsaDurango) |
| Laura | [@LauraSilRu](https://github.com/LauraSilRu) |
| María Roldán | [@Mary1922](https://github.com/Mary1922) |
| José Gregorio | [@GregDev08](https://github.com/GregDev08) |

---

## Documentación adicional

- [`docs/decisions/`](docs/decisions/) — ADRs (decisiones de arquitectura)
- [`docs/contract/`](docs/contract/) — Contrato de schemas API v1.0.0
- [`docs/architecture/`](docs/architecture/) — Diagramas de arquitectura
- [`docs/qa/`](docs/qa/) — Matriz de riesgos y plan de pruebas
- [`docs/legal/`](docs/legal/) — Textos RGPD y consentimiento
