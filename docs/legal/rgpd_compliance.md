# Privacidad y protección de datos — análisis inicial

**Estado:** borrador de trabajo; requiere validación del equipo y asesoramiento jurídico antes de presentar Avizor como conforme o usarlo con datos reales.

**Ámbito:** diseño previsto en los issues; todavía no hay implementación ni contrato de datos versionado que permita verificar controles.

Este documento identifica cuestiones y controles que el equipo debe resolver. No es asesoramiento jurídico, no determina por sí solo la base jurídica de cada tratamiento y no declara cumplimiento del RGPD o de la LOPDGDD.

## Marco y principios aplicables

El diseño debe analizar, como mínimo, los principios del artículo 5 del RGPD (licitud, lealtad y transparencia; limitación de finalidad; minimización; exactitud; limitación del plazo de conservación; integridad/confidencialidad y responsabilidad proactiva), una base jurídica válida para cada finalidad (artículo 6), la información a las personas (artículos 12–14), privacidad desde el diseño y por defecto (artículo 25), seguridad (artículo 32), registro de actividades cuando corresponda (artículo 30) y la necesidad de una evaluación de impacto (artículo 35). Si mensajes o adjuntos revelan categorías especiales, debe analizarse también el artículo 9.

La edad avanzada no implica por sí sola incapacidad ni autoriza a un tercero a consentir en nombre de la persona. La relación de tutor debe distinguirse de una representación legal válida. El equipo debe definir quién es responsable del tratamiento, si existe corresponsabilidad o encargado, las finalidades y la base jurídica antes de incorporar datos reales.

## Inventario preliminar y minimización

Los siguientes elementos provienen de los issues, no de un esquema de datos verificado:

| Dato/flujo previsto | Riesgo y tratamiento recomendado para el diseño |
|---|---|
| Mensaje o texto analizado | Puede contener identificadores, conversaciones privadas o datos sensibles. Minimizarlo en el dispositivo y antes de enviarlo; no persistir el texto en claro si el requisito del proyecto lo prohíbe; definir si el análisis local permite evitar la transferencia. |
| Remitente/teléfono | Un HMAC puede reducir exposición directa, pero si es enlazable o puede asociarse a una persona sigue siendo dato seudonimizado, no anónimo. Limitar finalidad, accesos, retención y protección de la clave; evitar incluir el número real en registros. |
| Imágenes, audio y documentos | No conservar binarios salvo necesidad aprobada. Definir extracción/anonimización, almacenamiento temporal, terceros que reciben el contenido y borrado. La decisión de arquitectura multimodal del ADR #7 está pendiente. |
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

- El requisito del issue #52 indica que `analyses` no debe contener texto en claro, que los adjuntos guardan solo metadatos y que `sender` contiene un HMAC en vez del teléfono. Confirmar estos puntos contra el contrato y el esquema implementado antes de considerarlos controles efectivos.
- La sustitución de nombres, teléfonos u otros identificadores reduce exposición, pero no garantiza anonimización si el mensaje todavía puede identificar a alguien por contexto. Tratar texto transformado y HMAC como datos personales mientras exista posibilidad razonable de reidentificación.
- Evitar que contenido original alcance logs, telemetría, excepciones, herramientas de depuración, prompts de terceros o datos de entrenamiento. Probar también el camino de error, no solo respuestas exitosas.
- Limitar permisos y acceso a claves y bases de datos; separar secretos de configuración versionada; usar transporte y almacenamiento protegidos y auditar accesos apropiadamente.
- Rechazar, antes de persistir, entradas declaradas no anonimizadas cuando así lo exige el contrato (`422 CONTENT_NOT_ANONYMIZED`, según el issue #52).

## Retención y borrado

El issue #49 propone los plazos `green: 0 días`, `amber: 7 días`, `red: 30 días` y `caso abierto: cierre + 90 días`. **Son propuestas pendientes de aprobación, no plazos impuestos por el RGPD ni política ya implementada.** Antes de adoptarlos, el equipo debe:

1. Precisar a qué entidad y finalidad aplica cada plazo (texto temporal, metadatos, análisis, alerta, logs, backups y evidencia de consentimiento no son necesariamente el mismo tratamiento).
2. Justificar cada plazo por necesidad y base jurídica, explicar el inicio del cómputo y resolver qué significa “caso abierto” y quién lo cierra.
3. Definir qué ocurre al revocar el consentimiento, cerrar una cuenta, recibir una solicitud de supresión o existir una obligación legal distinta.
4. Implementar y probar borrado efectivo en base de datos y, según diseño, copias, índices, colas y proveedores; conservar evidencia mínima del borrado sin duplicar datos personales.
5. Definir responsable, frecuencia, monitorización, reintentos, alertas y tratamiento de fallos del job del issue #19.

## Derechos, proveedores y evaluación de impacto

- Definir un canal y un procedimiento para solicitudes de acceso, rectificación, supresión, limitación, oposición y portabilidad cuando procedan; verificar identidad de forma proporcionada y responder en los plazos legales aplicables.
- Determinar los roles de responsables/encargados y formalizar acuerdos de tratamiento; evaluar transferencias internacionales antes de realizarlas.
- Evaluar y documentar, antes del piloto, si el tratamiento probablemente entraña alto riesgo y requiere EIPD conforme al artículo 35. Considerar la escala, monitorización, personas potencialmente vulnerables, datos y automatización; consultar a la autoridad de control si el análisis legal concluye que existe alto riesgo residual no mitigado.
- La aplicación de la Ley de IA de la UE, la clasificación del sistema, obligaciones del proveedor/desplegador y calendario aplicable deben revisarse cuando se conozca el uso previsto, arquitectura y fecha de puesta en servicio. Este documento no clasifica Avizor.
- Mantener una evaluación ética e inclusiva separada y coordinada con la [evaluación de impacto ético](./etica_inclusividad.md).

## Criterios de verificación pendientes

No declarar cumplimiento hasta demostrar al menos: inventario y base jurídica aprobados; avisos y consentimientos coherentes entre app y documentación; minimización antes de transferencias; ausencia de contenido personal en persistencia no permitida y logs; control de acceso; plazos aprobados e implementados; prueba de borrado/retirada; inventario y revisión de proveedores; procedimiento de derechos; y decisión documentada sobre EIPD y normativa de IA.

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
