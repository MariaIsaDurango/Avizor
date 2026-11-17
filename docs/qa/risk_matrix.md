# Matriz inicial de riesgos

**Estado:** inicial y cualitativa; pendiente de revisión con el equipo.

**Alcance:** riesgos de calidad, seguridad, privacidad, IA e inclusión identificados en los issues y en el estado actual del repositorio.

Esta matriz no sustituye un análisis de amenazas ni una evaluación de impacto en protección de datos (EIPD). La probabilidad no se ha medido: las etiquetas son estimaciones preliminares para ordenar trabajo, no resultados de pruebas.

## Escala

- **Probabilidad:** baja / media / alta, a revisar con evidencia y arquitectura.
- **Impacto:** moderado / alto / muy alto, considerando seguridad de la persona usuaria, privacidad y disponibilidad.
- **Prioridad inicial:** crítica / alta / media. Se revisa tras implementar controles y probarlos.
- **Estado:** pendiente hasta que exista evidencia verificable del control.

## Registro

| ID | Riesgo y escenario | Probabilidad inicial | Impacto | Prioridad | Controles y prueba de verificación | Responsable/estado |
|---|---|---:|---:|---:|---|---|
| R-01 | Un falso negativo clasifica un phishing, smishing o vishing como seguro y la persona sigue instrucciones fraudulentas. | Media | Muy alto | Crítica | Evaluación por canal y clase; revisar recall, matriz de confusión, límites y comportamiento ante incertidumbre; casos de prueba revisados por el equipo. | ML + QA; pendiente del modelo y ADR de métricas. |
| R-02 | Falsos positivos bloquean mensajes legítimos o erosionan la confianza de la persona mayor. | Media | Alto | Alta | Medir precisión y falsos positivos; flujo de revisión/desbloqueo accesible; registrar la decisión del usuario y probar reversibilidad autorizada. | ML + producto + QA; pendiente. |
| R-03 | Una instrucción maliciosa dentro del mensaje, fuente RAG o adjunto induce al agente a cambiar su veredicto o acciones. | Media | Muy alto | Crítica | Separar instrucciones de datos; limitar herramientas; validar salida contra esquema y enum; pruebas adversariales sintéticas y comportamiento de contingencia. | Backend/IA + QA; pendiente (#51). |
| R-04 | Mensaje, teléfono, adjunto, credencial o dato sensible aparece en base de datos, logs, telemetría o proveedor externo. | Media | Muy alto | Crítica | Minimización y anonimización antes de transferir; HMAC tratado como dato seudonimizado; revisar logs/BD/trazas; controlar claves y accesos; comprobar contratos de encargados/transferencias. | Backend + privacidad; pendiente (#49, #52). |
| R-05 | Retención o purga incorrecta conserva contenido más tiempo del informado o elimina datos necesarios sin proceso definido. | Media | Alto | Alta | Implementación encontrada para texto, desbloqueos e indicadores; revisar y aprobar los plazos por finalidad, ejecutar tests de fechas límite/reintentos en PostgreSQL y verificar despliegue, backups y terceros. | Implementado parcialmente en backend; tests de retención locales omitidos por falta de PostgreSQL; aprobación de privacidad pendiente (#19, #49, #52). |
| R-06 | Autorización incorrecta permite acceso de tutor/sénior a datos o acciones de otra persona/dispositivo. | Media | Muy alto | Crítica | Autorización por recurso, pruebas negativas de rol y propiedad, expiración de tokens, aislamiento de datos; auditar errores sin revelar existencia de terceros. | Backend + QA; pendiente (#50). |
| R-07 | Consentimiento ausente, no informado, no demostrable o atribuido indebidamente a un tutor/representante. | Media | Muy alto | Crítica | Describir finalidades y datos en lenguaje accesible; separar consentimientos cuando corresponda; permitir retirada; verificar autoridad de representación y no inferirla solo por la relación de tutor. | Producto + privacidad/legal; pendiente (#49). |
| R-08 | AccessibilityService, NotificationListenerService o CallScreeningService accede a más contenido del necesario o sorprende a la persona usuaria. | Media | Muy alto | Alta | Limitar eventos/datos/permisos; explicar activación y alcance; desactivar sin penalización; revisar políticas de Android/Google Play y probar en dispositivo. | Mobile/Android + QA; pendiente (#31, #32, #49). |
| R-09 | Rendimiento desigual o datos de evaluación no representativos generan protección insuficiente para idioma, canal o perfil de usuario. | Media | Alto | Alta | Documentar procedencia/licencia y composición de datos; métricas por subgrupos cuando sean éticas y tengan tamaño suficiente; informar incertidumbre y limitaciones. | ML + QA; pendiente (#33–#37). |
| R-10 | La persona confía excesivamente en el resultado, o no entiende por qué se bloqueó un mensaje ni cómo pedir ayuda. | Media | Alto | Alta | Mensajes claros, no alarmistas y accesibles; explicar límites; revisión humana y recuperación apropiada; pruebas de usabilidad/inclusión. | Producto + QA; pendiente. |
| R-11 | Una dependencia/servicio de IA o reputación comparte datos con terceros o fuera del EEE sin base y garantías comprobadas. | Media | Muy alto | Alta | Inventariar proveedores, datos, ubicación, subencargados, entrenamiento y conservación; evaluación contractual y de transferencias antes de enviar datos reales. | Privacidad + arquitectura; proveedores por decidir (#7). |
| R-12 | CI informa verde aunque omita suites que aún no existen, creando una falsa sensación de cobertura. | Alta | Alto | Alta | Hacer visible qué suites se ejecutaron y cuáles se omitieron; convertir requisitos de cobertura en puertas explícitas al implementarse los módulos; revisar CI junto con los tests. | Ingeniería + QA; actualmente CI omite mobile/ML o backend cuando faltan archivos. |

## Tratamiento y revisión

1. Confirmar con cada responsable si el escenario aplica y quién implementa el control, sin asumir tareas asignadas a otros.
2. Convertir riesgos críticos/altos en requisitos y casos de prueba rastreables.
3. Registrar riesgo residual, evidencia, responsable y fecha de revisión cuando exista una mitigación.
4. Revisar esta matriz al decidir arquitectura/modelos, incorporar proveedores, habilitar funciones Android y antes de pilotos con personas reales.

## Fuentes de requisitos

- Issues del proyecto: [#7](https://github.com/MariaIsaDurango/Avizor/issues/7), [#19](https://github.com/MariaIsaDurango/Avizor/issues/19), [#31](https://github.com/MariaIsaDurango/Avizor/issues/31), [#32](https://github.com/MariaIsaDurango/Avizor/issues/32), [#48](https://github.com/MariaIsaDurango/Avizor/issues/48), [#49](https://github.com/MariaIsaDurango/Avizor/issues/49), [#50](https://github.com/MariaIsaDurango/Avizor/issues/50), [#51](https://github.com/MariaIsaDurango/Avizor/issues/51) y [#52](https://github.com/MariaIsaDurango/Avizor/issues/52).
- Para protección de datos y evaluación formal del tratamiento, véase [documentación legal inicial](../legal/rgpd_compliance.md).
