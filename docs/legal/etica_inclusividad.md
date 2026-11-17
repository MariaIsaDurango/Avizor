# Evaluación ética e inclusiva inicial

**Estado:** borrador para discusión del equipo; no sustituye una evaluación con personas usuarias ni asesoramiento legal.

**Población prevista:** personas mayores usuarias del modo sénior y sus tutores, según el diseño del proyecto.

Avizor pretende ayudar a identificar posibles estafas, pero puede afectar decisiones, autonomía, privacidad y confianza. La edad no debe usarse como sustituto de una evaluación individual de necesidades o capacidad. Esta evaluación inicial identifica preguntas y salvaguardas que deben validarse antes de un piloto.

## Riesgos éticos y salvaguardas propuestas

| Tema | Riesgo | Salvaguarda a validar |
|---|---|---|
| Autonomía | El tutor o el bloqueo automático sustituye la decisión de la persona mayor. | Explicar quién decide cada acción; conservar control y vías de recuperación apropiadas; no permitir que el tutor acceda a más información de la necesaria. |
| Consentimiento y dignidad | La interfaz presupone incapacidad por edad o presiona a aceptar vigilancia. | Lenguaje respetuoso y accesible; alternativas claras; consentimiento específico y revocable; no inferir incapacidad por edad. |
| Errores de IA | Falso negativo expone a una estafa; falso positivo bloquea una comunicación legítima y genera ansiedad. | Expresar incertidumbre; alertas proporcionales y comprensibles; revisión humana donde aplique; mecanismo seguro de corrección/desbloqueo; medir ambos tipos de error. |
| Sesgo y representatividad | El sistema funciona peor según lenguaje, región, canal, discapacidad o familiaridad digital. | Documentar composición y límites de datos; análisis por subgrupos solo con datos lícitos y suficientes; pruebas con contenido benigno diverso y revisión de accesibilidad. |
| Opacidad | La persona no sabe por qué se inspeccionan notificaciones o qué datos llegan a un servicio externo. | Aviso previo sobre alcance, permisos, proveedores, conservación y límites; controles para activar/desactivar y consultar el estado. |
| Dependencia excesiva | La app se presenta como garantía de seguridad o induce a obedecer el resultado. | No prometer detección completa; recomendar verificación por canales independientes; ofrecer instrucciones claras de ayuda y reporte. |
| Accesibilidad Android | El acceso a contenido de pantalla o llamadas supera lo necesario o no es comprensible. | Revisar necesidad funcional y políticas de plataforma; limitar eventos y datos; explicar permisos especiales y probar activación/desactivación en dispositivos reales. |
| Protección de datos | El mensaje analizado o el número de teléfono se revela a tutores, logs o terceros sin necesidad. | Minimización, seudonimización, acceso por rol, retención limitada y pruebas de privacidad de extremo a extremo. |

## Evaluación previa a un piloto

1. Definir población, contexto de uso, decisiones automatizadas y límites del sistema.
2. Revisar materiales y flujos con personas mayores de perfiles diversos, con participación voluntaria, accesible y debidamente autorizada; no recopilar más datos de los necesarios.
3. Probar comprensión de permisos, consentimiento, mensajes de amenaza, falsos positivos, retirada y recuperación.
4. Registrar hallazgos de forma agregada y sin datos identificables; asignar responsables y verificar las correcciones.
5. Acordar un proceso de incidentes y una alternativa de soporte humano; no usar la app como único canal para situaciones urgentes.
6. Volver a evaluar tras cambios sustanciales de modelo, proveedor, permisos, población o finalidad.

## Preguntas abiertas para el equipo

- ¿Qué acciones puede realizar Avizor automáticamente y cuáles requieren confirmación del sénior o tutor?
- ¿Cómo se resuelve el desacuerdo entre sénior y tutor? ¿Qué autoridad se verifica en `legal_guardianship`?
- ¿Qué explicación recibe la persona ante cada veredicto y cómo se evita que se interprete como certeza?
- ¿Qué diversidad lingüística, regional, de accesibilidad y de dispositivos cubrirá la evaluación?
- ¿Cómo se informa y atiende un falso positivo, una falsa alarma o una detección tardía?
- ¿Qué datos ve el tutor y cuáles permanecen privados para el sénior?

## Fuentes y relación con otros documentos

- [Plan de pruebas](../qa/test_plan.md) — criterios funcionales, evaluación de modelos y pruebas Android.
- [Matriz de riesgos](../qa/risk_matrix.md) — registro inicial de impacto y salvaguardas.
- [Privacidad y protección de datos](./rgpd_compliance.md) — transparencia, base jurídica, derechos y EIPD.
- [Guías oficiales de la AEPD](https://www.aepd.es/guias-y-herramientas/guias).
- [Guía de Android sobre servicios de accesibilidad](https://developer.android.com/guide/topics/ui/accessibility/service).

Pendiente: revisión con el equipo, alineación con el contrato y las decisiones técnicas del issue [#7](https://github.com/MariaIsaDurango/Avizor/issues/7), y aprobación antes de cualquier prueba con personas reales.
