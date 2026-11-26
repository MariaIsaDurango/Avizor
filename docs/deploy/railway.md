# Despliegue del backend en Railway (#122)

El backend (API + portal web) se despliega como un contenedor Docker con
`backend/Dockerfile`. La base de datos es el PostgreSQL de Railway.

No usamos `railway.json`: Railway lo ha marcado como obsoleto (Config as Code)
y los servicios nuevos no pueden usarlo. Todo se configura con variables y
desde el panel.

## Qué hace el contenedor al arrancar

`backend/docker-entrypoint.sh`:

1. `alembic upgrade head`: aplica las migraciones pendientes. Si falla, el
   contenedor no arranca.
2. `uvicorn app.main:app` en el puerto `PORT` que da Railway, con un solo
   proceso (la purga de retención corre dentro de la app y no debe duplicarse).

La imagen se construye desde la raíz del repo porque el backend importa
`rag/src/reputation` (#42). Solo copia lo necesario para ejecutar: sin tests,
sin `mobile/` y sin `ml/`.

## Pasos en Railway

1. **New Project → Deploy from GitHub repo** → `MariaIsaDurango/Avizor`.
   - Rama: `main` (o `dev` para pruebas).
   - Root Directory: vacío (la raíz del repo).
2. **+ New → Database → PostgreSQL** en el mismo proyecto.
3. En el servicio del backend, pestaña **Variables**:

   | Variable | Valor |
   |---|---|
   | `RAILWAY_DOCKERFILE_PATH` | `backend/Dockerfile` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia al servicio de Postgres) |
   | `JWT_SECRET` | 64 caracteres aleatorios: `openssl rand -hex 32` |
   | `PHONE_HMAC_KEY` | otros 64 caracteres distintos: `openssl rand -hex 32` |
   | `APP_ENV` | `production` |
   | `FRONTEND_URL` | `https://<dominio-de-railway>` (paso 4) |
   | `MAIL_PROVIDER` | `brevo` (o `log` mientras no haya clave: el código sale en los logs) |
   | `BREVO_API_KEY` | clave de API de Brevo (SMTP & API → API Keys) |
   | `MAIL_FROM` | `Avizor <avizorapp1.0@gmail.com>` (remitente verificado en Brevo) |
   | `PUSH_PROVIDER` | `expo` (cuando la app tenga push real; si no, `log`) |

   `DATABASE_URL` puede llegar como `postgresql://...`: el backend lo convierte
   solo a `postgresql+psycopg://...`.

   **Correo:** Railway bloquea el SMTP saliente (puertos 25, 465, 587 y 2525)
   en los planes Free, Trial y Hobby, así que `MAIL_PROVIDER=smtp` (Gmail) no
   funciona allí. Se usa la API HTTPS de Brevo. En local se puede seguir usando
   `smtp` con Gmail o `log`.

   El RAG (#143) está apagado por defecto: ver la sección **RAG (#143)**.

4. **Settings → Networking → Generate Domain**. Copia la URL y ponla en
   `FRONTEND_URL`.
5. **Settings → Deploy → Healthcheck Path**: `/api/v1/health`.
6. Despliega y comprueba:

   ```
   https://<dominio>/api/v1/health
   → {"status":"ok","contract_version":"1.0.0"}
   ```

## Modelo de IA (#38)

El clasificador de IA (BETO de 3 clases en ONNX int8, 111 MB) no está en el
repo: GitHub no admite archivos de más de 100 MB. Se publica como adjunto de una
**release de GitHub** y el Dockerfile lo descarga al construir la imagen,
comprobando su SHA-256. Si el SHA-256 no coincide, el build falla.

Variables del servicio del backend:

| Variable | Valor |
|---|---|
| `ML_MODEL_URL` | `https://github.com/MariaIsaDurango/Avizor/releases/download/<tag>/avizor-3c-onnx.zip` |
| `ML_MODEL_SHA256` | el SHA-256 del zip (se indica en la release) |
| `CLASSIFIER_PROVIDER` | `ml` (`keywords` vuelve a las reglas sin redesplegar el modelo) |
| `ML_FRAUD_THRESHOLD` | opcional; vacío = el umbral del paquete del modelo |

- Railway pasa estas variables al build porque el Dockerfile las declara con
  `ARG`. Sin `ML_MODEL_URL` la imagen se construye igual y usa las reglas.
- Si el modelo no se puede cargar al arrancar, la API sigue funcionando con
  las reglas y lo deja escrito en los logs ("ML classifier could not be
  loaded").
- Memoria: con el modelo cargado la API ocupa unos 360 MB (medido en local;
  sin modelo, unos 95 MB). Comprueba en **Metrics** que el plan lo admite.
- Para cambiar de modelo: nueva release con el zip nuevo y actualizar
  `ML_MODEL_URL` y `ML_MODEL_SHA256`.

## Después del despliegue

- **App móvil**: en `mobile/.env.local`,
  `EXPO_PUBLIC_API_URL=https://<dominio>`. Para builds con EAS, la misma
  variable en `eas.json` o en el panel de EAS.
- **Portal web**: se sirve desde el mismo dominio, no hay que cambiar nada.
- Los secretos solo van en las variables de Railway, nunca en el repo.

## Probar la imagen en local (opcional, con Docker Desktop)

```
docker build -f backend/Dockerfile -t avizor-backend .
docker run --rm -p 8000:8000 --env-file .env avizor-backend
```

Con la base de datos de `docker-compose.yml`, en el `.env` usa
`host.docker.internal` en lugar de `localhost` en `DATABASE_URL`.

## RAG (#143)

El RAG del análisis manual usa Groq y la base ChromaDB de avisos oficiales.
Está **apagado por defecto** porque torch y el modelo E5 añaden varios GB a la
imagen. Sin él, la vía rápida (clasificador + reputación) funciona igual.

Para activarlo, cuando el volumen de ChromaDB esté listo:

| Variable | Valor |
|---|---|
| `INSTALL_RAG` | `true` (se usa al construir: instala torch CPU, dependencias del RAG y E5) |
| `GROQ_API_KEY` | clave de Groq (nunca en el repo) |
| `GROQ_MODEL` | `openai/gpt-oss-20b` |
| `CHROMA_PATH` | carpeta del volumen montado con `chroma.sqlite3` |
| `AVIZOR_RAG_ENABLED` | `true`, solo después de comprobar lo anterior |

E5 se descarga en la revisión fija `d128750597153bb5987e10b1c3493a34e5a4502a`,
la misma con la que se creó la base ChromaDB. Para volver atrás basta con
`AVIZOR_RAG_ENABLED=false`; con `INSTALL_RAG=false` la imagen vuelve a su
tamaño normal en el siguiente despliegue.

Groq se llama sin reintentos (`max_retries=0`), por decisión: el agente tiene un
plazo y un reintento lo agotaría. Si Groq falla, se usa la vía rápida.

Privacidad: el texto anonimizado del análisis manual se envía a Groq. La
anonimización actual no quita nombres de personas ni enlaces. Decisión pendiente
de documentar por José (privacidad).

## Teléfonos: prefijo 400 y OpenSpam (#168)

**Prefijo 400 (siempre activo, sin API):** desde el 17/10/2026 las llamadas
comerciales en España solo pueden hacerse desde números de 9 cifras que empiezan
por 400. Al comprobar un número `+34 400 ...` la vía rápida devuelve ámbar
`spam` con confianza 0,95. Es publicidad legal, no estafa: nunca rojo por sí
solo (sí con 5 reportes de usuarios).

**OpenSpam (apagado por defecto):** consulta `api.openspam.es` cuando se
comprueba un número español. Para activarlo, **después de que José valide la
privacidad** (el número viaja a un tercero dentro de la URL, por HTTPS):

| Variable | Valor |
|---|---|
| `AVIZOR_EXTERNAL_PHONES` | `1` |
| `AVIZOR_OPENSPAM_KEY` | clave de OpenSpam (nunca en el repo) |
| `AVIZOR_PHONE_BUDGET_MS` | `600` (espera máxima; 100–700) |

- Plan gratuito: solo uso no comercial; 50 consultas/día, 20/hora y 2 s entre
  consultas. El backend respeta esos límites; si se agotan, sigue sin OpenSpam.
- Caché en memoria de 24 h por número (claves HMAC, nunca en disco).
  Pendiente de confirmar con OpenSpam: su documentación permite guardar
  resultados hasta 24 h en planes de pago y no lo detalla para el gratuito.
- Si OpenSpam tarda más que el presupuesto o falla, vale la decisión local; la
  consulta termina en segundo plano y llena la caché.
- Un positivo de OpenSpam sube el riesgo (alto/muy alto → rojo; medio/bajo →
  ámbar) pero no crea un reporte local del número. No encontrado: sin cambio.
- Para desactivarlo basta con `AVIZOR_EXTERNAL_PHONES=0`.


## OCR y nombres en archivos (#192, #193)

- **OCR de imágenes:** Tesseract va dentro de la imagen Docker. No hay que
  configurar nada.
- **Nombres de personas** en el texto de PDF e imágenes: spaCy local, sin
  terceros. El modelo se instala con `requirements.txt` y se carga la primera
  vez que alguien envía un archivo.

| Variable | Valor |
|---|---|
| `AVIZOR_NER_MODEL` | `es_core_news_md` (por defecto, unos 350 MB de RAM al cargarse) |

- Con el plan Free (0,5 GB por servicio) el modelo md no cabe: usar
  `es_core_news_sm` (unos 160 MB, falla más) o dejar la variable vacía para
  desactivarlo. Con `sm` hay que añadir ese modelo a `requirements.txt`.
- Sin modelo sigue activa la regla de tratamientos (Sr., Doña, Titular:...).
