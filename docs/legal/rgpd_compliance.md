# Privacidad y protección de datos — análisis inicial

**Estado:** borrador de trabajo; requiere validación del equipo y asesoramiento jurídico antes de presentar Avizor como conforme o usarlo con datos reales.

**Ámbito:** análisis del contrato v1.0.0 declarado por el backend, sus esquemas y migración Alembic, y los controles implementados en el código revisado. La existencia de estos controles no acredita por sí sola el cumplimiento legal, la configuración del despliegue ni la aprobación del equipo.

Este documento identifica cuestiones y controles que el equipo debe resolver. No es asesoramiento jurídico, no determina por sí solo la base jurídica de cada tratamiento y no declara cumplimiento del RGPD o de la LOPDGDD.

## Marco y principios aplicables

El diseño debe analizar, como mínimo, los principios del artículo 5 del RGPD (licitud, lealtad y transparencia; limitación de finalidad; minimización; exactitud; limitación del plazo de conservación; integridad/confidencialidad y responsabilidad proactiva), una base jurídica válida para cada finalidad (artículo 6), la información a las personas (artículos 12–14), privacidad desde el diseño y por defecto (artículo 25), seguridad (artículo 32), registro de actividades cuando corresponda (artículo 30) y la necesidad de una evaluación de impacto (artículo 35). Si mensajes o adjuntos revelan categorías especiales, debe analizarse también el artículo 9.

La edad avanzada no implica por sí sola incapacidad ni autoriza a un tercero a consentir en nombre de la persona. La relación de tutor debe distinguirse de una representación legal válida. El equipo debe definir quién es responsable del tratamiento, si existe corresponsabilidad o encargado, las finalidades y la base jurídica antes de incorporar datos reales.

## Inventario preliminar y minimización

Los siguientes elementos se contrastan con los esquemas y modelos actuales del backend. La versión `1.0.0` está declarada en la configuración de la API; no se encontró una especificación normativa independiente en `docs/contract/`, por lo que los esquemas del backend son la referencia técnica disponible.

| Dato/flujo previsto | Riesgo y tratamiento recomendado para el diseño |
|---|---|
| Mensaje o texto analizado | El backend no guarda el texto en `analyses`; el texto anonimizado se conserva temporalmente en `temp_content` y se purga según las reglas descritas abajo. El endpoint rechaza `anonymization.applied=false` con `422 CONTENT_NOT_ANONYMIZED`; esto no demuestra que cada texto marcado como anonimizado haya sido redactado correctamente. |
| Remitente/teléfono | El backend persiste un HMAC-SHA256 del remitente y una versión enmascarada, no el teléfono original en claro. Los tests cubren normalización, enmascarado y hash. El HMAC sigue siendo dato seudonimizado si puede enlazarse o asociarse a una persona; hay que proteger la clave y limitar finalidad y acceso. |
| Imágenes, audio y documentos | El modelo de base de datos guarda metadatos de adjuntos, no el binario original. El esquema describe una vía `multipart` para reenvío manual, pero el endpoint de análisis revisado implementa la vía rápida JSON; el procesamiento en memoria y la transferencia multimodal deben verificarse al completar esa ruta. La decisión de arquitectura multimodal del ADR #7 está pendiente. |
| Consentimiento, cuenta, pairing y alertas | Minimizar atributos y separar datos de cuenta de contenido analizado. Definir controles de acceso, trazabilidad, rectificación/borrado y efectos de revocar consentimiento. |
| Registros técnicos y métricas | Excluir texto, teléfonos, tokens y contenido de adjuntos; usar identificadores efímeros y agregados cuando sea posible; fijar acceso y retención específicos para logs. |
| Datos de datasets/modelos | Documentar origen, licencia, restricciones, calidad y posible información personal; no incorporar conjuntos sin una revisión de procedencia y uso permitido. |

Antes de habilitar un proveedor de IA, scraping o reputación, documentar qué dato recibe, para qué, dónde, durante cuánto tiempo, si lo utiliza para entrenar, subencargados, mecanismo de transferencia y garantías. No enviar datos reales a un proveedor hasta completar esa revisión y aprobar la arquitectura.

## Transparencia, consentimiento y representación

El issue #49 plantea flujos `self` y `legal_guardianship`; son etiquetas del proyecto, no una conclusión jurídica.

- Presentar información por capas y en lenguaje claro, accesible y comprensible para la persona mayor: responsable, finalidad, datos, destinatarios/proveedores, conservación, derechos, contacto y consecuencias de no consentir.
- Si el consentimiento es la base jurídica, debe comprobarse que sea libre, específico, informado e inequívoco, que pueda demostrarse y retirarse con facilidad comparable a otorgarlo. Separar finalidades incompatibles y evitar que el acceso a funciones no relacionadas dependa de consentimientos innecesarios.
- No asumir que una cuenta de tutor, vínculo familiar o pairing acredita representación legal. Definir cómo verificar la autoridad, su alcance y vigencia; respetar la voluntad y derechos de la persona representada y confirmar con asesoría legal el marco español aplicable.
- Diseñar y documentar retirada del consentimiento, oposición u otras solicitudes según la base jurídica, incluyendo efectos sobre análisis pendientes, alertas, contenido temporal y datos que deban conservarse por otra obligación.
- Mantener evidencia mínima del consentimiento y sus cambios, sin guardar una copia del contenido analizado como prueba del consentimiento.

## Anonimización, seudonimización y seguridad

- El backend declara el contrato `1.0.0`, contiene esquemas Pydantic y una migración Alembic. En el modelo actual, `analyses` no guarda el texto del mensaje, `temp_content` guarda el texto anonimizado con vencimiento y `analysis_attachments` guarda metadatos, no binarios originales. Véanse [configuración de versión](../../backend/app/core/config.py), [modelos](../../backend/app/models/analysis.py) y [migración inicial](../../backend/migrations/versions/0001_initial_schema.py).
- Si `anonymization.applied` es `false`, el backend devuelve `422 CONTENT_NOT_ANONYMIZED`; hay una prueba de integración para este rechazo en [test_analyses_fast.py](../../backend/tests/test_analyses_fast.py). El servidor recibe una declaración del cliente: no verifica por sí mismo que el NER haya eliminado todos los identificadores.
- El remitente se transforma con HMAC-SHA256 y el valor público se enmascara; [test_privacy.py](../../backend/tests/test_privacy.py) cubre estos comportamientos. El hash no debe describirse como dato anónimo.
- El modelo de adjuntos declara que no persiste el archivo original y solo guarda metadatos. No se debe afirmar que la ruta multimodal completa ya procesa los archivos en memoria: el endpoint revisado solo implementa la vía rápida JSON y el propio código remite el reenvío multipart a la issue #15.
- La sustitución de nombres, teléfonos u otros identificadores reduce exposición, pero no garantiza anonimización si el mensaje todavía puede identificar a alguien por contexto. Tratar texto transformado y HMAC como datos personales mientras exista posibilidad razonable de reidentificación.
- Evitar que contenido original alcance logs, telemetría, excepciones, herramientas de depuración, prompts de terceros o datos de entrenamiento. Probar también el camino de error, no solo respuestas exitosas.
- Limitar permisos y acceso a claves y bases de datos; separar secretos de configuración versionada; usar transporte y almacenamiento protegidos y auditar accesos apropiadamente.
- Rechazar, antes de persistir, entradas declaradas no anonimizadas (`422 CONTENT_NOT_ANONYMIZED`); este comportamiento tiene una prueba automatizada.

## Retención y borrado

El issue #49 propuso `green: 0 días`, `amber: 7 días`, `red: 30 días` y, ante un caso, conservar el texto hasta 90 días después de su cierre. **En el backend revisado, la purga ya está implementada conforme a esas reglas para el contenido temporal, además de las reglas de desbloqueos e indicadores.** Esto describe el comportamiento del código; no significa que el equipo haya aprobado jurídicamente la necesidad de cada plazo ni demuestra por sí solo el borrado en producción.

### Comportamiento implementado en el backend revisado

- **Texto temporal (`temp_content`):** el servicio asigna 7 días a resultados `amber` y 30 días a `red`. No persiste texto temporal para `green`. La purga elimina filas cuyo `delete_at` ya venció, salvo si hay un caso abierto o cerrado hace menos de 90 días; en esos casos conserva el texto hasta 90 días después del cierre. A los 90 días exactos deja de aplicar la retención del caso y el texto vencido puede eliminarse.
- **Metadatos del análisis:** la operación elimina la fila de `temp_content`, no la de `analyses`; así se conservan los metadatos que utilizan las estadísticas. La clave foránea de `temp_content` apunta a `analyses`, por lo que este borrado de la fila hija no borra el análisis.
- **Desbloqueos:** las solicitudes `pending_guardian` con `expires_at` vencido pasan a `expired`. El servicio establece `expires_at` a 24 horas desde la solicitud. También hay caducidad perezosa al consultar/resolver una solicitud; el job no es el único mecanismo.
- **Indicadores:** se eliminan si `last_seen_at` tiene al menos 365 días y no existe ningún caso asociado. La condición protege indicadores con cualquier caso asociado, incluso cerrado.
- **Ejecución:** `app.main` inicia el bucle al arrancar la API. `RETENTION_PURGE_MINUTES` vale 60 por defecto y `0` lo desactiva; el bucle ejecuta una purga inmediata y continúa al intervalo configurado. También se puede ejecutar una vez desde `backend` con `python -m app.jobs.purge`. Un bloqueo asesor de PostgreSQL evita que varias réplicas purguen a la vez; los fallos quedan en el log y no terminan el bucle.

Referencias de implementación: [reglas de retención](../../backend/app/services/retention.py), [job manual y periódico](../../backend/app/jobs/purge.py), [arranque de la API](../../backend/app/main.py), [asignación de vencimiento del contenido](../../backend/app/services/analysis.py) y [TTL de desbloqueo](../../backend/app/services/unlocks.py).

### Evidencia y límites de la verificación

Hay pruebas específicas en [test_retention.py](../../backend/tests/test_retention.py) para la eliminación del texto vencido, casos abiertos y cerrados, conservación de metadatos de análisis, expiración de desbloqueos y borrado/exclusión de indicadores. El **17 de noviembre de 2026** se ejecutó localmente la suite completa del backend con PostgreSQL 16 saludable y migraciones aplicadas: **250 passed, 1 warning**, incluidos los tests de retención. `ruff check` y `ruff format --check` también pasaron. La configuración de CI levanta PostgreSQL 16, aplica las migraciones y ejecuta `pytest backend/tests`; la fixture omite las pruebas que necesitan base de datos cuando no puede conectarse.

Las pruebas de privacidad del endpoint cubren HMAC, rechazo `422` y vencimientos `amber`/`red` en [test_analyses_fast.py](../../backend/tests/test_analyses_fast.py). [test_models.py](../../backend/tests/test_models.py) comprueba que el esquema de adjuntos contiene solo metadatos; la ruta multimodal aún requiere validación cuando esté integrada.

La suite de backend se ejecuta en CI con PostgreSQL; para reproducirla localmente debe estar disponible la base de pruebas. También deben revisarse fallos/reintentos, despliegue con varias réplicas, backups y sistemas externos si almacenan contenido. Un `.delete()` en la base de datos principal no prueba por sí solo el borrado de copias ni de proveedores.

Los plazos son decisiones del proyecto informadas por el contrato, no plazos que el RGPD imponga literalmente. El responsable del tratamiento debe justificar y aprobar su necesidad por finalidad. También debe aclararse qué datos distintos del texto temporal (por ejemplo, alertas, logs y evidencia de consentimiento) tienen sus propios plazos y cómo se atienden solicitudes de supresión u obligaciones legales.

## Derechos, proveedores y evaluación de impacto

- Definir un canal y un procedimiento para solicitudes de acceso, rectificación, supresión, limitación, oposición y portabilidad cuando procedan; verificar identidad de forma proporcionada y responder en los plazos legales aplicables.
- Determinar los roles de responsables/encargados y formalizar acuerdos de tratamiento; evaluar transferencias internacionales antes de realizarlas.
- Evaluar y documentar, antes del piloto, si el tratamiento probablemente entraña alto riesgo y requiere EIPD conforme al artículo 35. Considerar la escala, monitorización, personas potencialmente vulnerables, datos y automatización; consultar a la autoridad de control si el análisis legal concluye que existe alto riesgo residual no mitigado.
- La aplicación de la Ley de IA de la UE, la clasificación del sistema, obligaciones del proveedor/desplegador y calendario aplicable deben revisarse cuando se conozca el uso previsto, arquitectura y fecha de puesta en servicio. Este documento no clasifica Avizor.
- Mantener una evaluación ética e inclusiva separada y coordinada con la [evaluación de impacto ético](./etica_inclusividad.md).

## Criterios de verificación pendientes

No declarar cumplimiento hasta demostrar al menos: inventario y base jurídica aprobados; avisos y consentimientos coherentes entre app y documentación; minimización antes de transferencias; ausencia de contenido personal en persistencia no permitida y logs; control de acceso; plazos aprobados; borrado/retirada verificados en despliegue; inventario y revisión de proveedores; procedimiento de derechos; y decisión documentada sobre EIPD y normativa de IA. La purga está implementada y sus pruebas locales y de CI se ejecutaron con PostgreSQL; siguen pendientes la aprobación legal, las comprobaciones operativas y la verificación de backups o proveedores.

La revisión técnica deberá usar datos sintéticos. Cualquier prueba con personas o mensajes reales exige aprobación previa, base y salvaguardas apropiadas.

## Fuentes oficiales de referencia

Consultadas para preparar este borrador el **13 de noviembre de 2026**; el equipo debe revisar las versiones vigentes antes de una entrega legal:

- [Reglamento (UE) 2016/679 (RGPD), EUR-Lex, texto en español](https://eur-lex.europa.eu/eli/reg/2016/679/oj?locale=es).
- [Ley Orgánica 3/2018 (LOPDGDD), BOE, texto consolidado](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673).
- [Guías de la Agencia Española de Protección de Datos (AEPD)](https://www.aepd.es/guias-y-herramientas/guias).
- [Directrices 05/2020 del Comité Europeo de Protección de Datos sobre consentimiento (EDPB)](https://www.edpb.europa.eu/documents/guideline/guidelines-052020-on-consent-under-regulation-2016679_en).
- [Reglamento (UE) 2024/1689 (Ley de IA), EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=es).
- [Guía de Android sobre servicios de accesibilidad](https://developer.android.com/guide/topics/ui/accessibility/service).

## Trazabilidad

Basado principalmente en los issues [#49](https://github.com/MariaIsaDurango/Avizor/issues/49), [#52](https://github.com/MariaIsaDurango/Avizor/issues/52), job de borrado [#19](https://github.com/MariaIsaDurango/Avizor/issues/19), decisiones pendientes [#7](https://github.com/MariaIsaDurango/Avizor/issues/7) y PoC Android [#31](https://github.com/MariaIsaDurango/Avizor/issues/31)/[#32](https://github.com/MariaIsaDurango/Avizor/issues/32).
