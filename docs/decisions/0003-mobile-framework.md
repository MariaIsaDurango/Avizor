# ADR 0003: React Native (Expo) como framework móvil

**Fecha:** 2026-11-18  
**Estado:** Aceptado  
**Autora:** Majo

---

## Contexto

Avizor necesita una app móvil cross-platform (iOS y Android) con dos modos diferenciados: Tutor y Sénior. El modo Sénior con protección automática requiere acceso a servicios nativos de Android: `AccessibilityService` para monitorizar la pantalla, `CallScreeningService` para interceptar llamadas entrantes y `NotificationListenerService` para leer notificaciones. Este modo es exclusivo de Android; iOS no expone APIs equivalentes para apps de terceros. El equipo tiene experiencia previa en TypeScript/JavaScript y el panel web ya está desarrollado en ese stack.

Las opciones evaluadas fueron React Native con Expo y Flutter.

---

## Alternativas consideradas

### React Native con Expo (development build)
- Mismo lenguaje que el panel web (TypeScript)
- Expo Go permite probar en dispositivo sin compilar durante el desarrollo
- El development build permite añadir módulos nativos cuando Expo SDK no es suficiente
- Ecosistema maduro con librerías para todo lo que necesita el proyecto (`expo-notifications`, `expo-secure-store`, `expo-haptics`, `@react-navigation`)

### Flutter
- Rendimiento de renderizado superior (motor Skia/Impeller propio)
- Consistencia visual perfecta entre plataformas
- Requiere aprender Dart — lenguaje que nadie del equipo conocía
- Ecosistema de librerías de accesibilidad nativa menos maduro en el momento de la decisión

---

## Decisión

**React Native con Expo (development build).**

El factor determinante fue la velocidad de desarrollo: el equipo domina TypeScript y Expo proporciona prácticamente todas las librerías necesarias sin configuración nativa adicional. Los módulos nativos de `CallScreeningService` y `NotificationListenerService` (PoC #31 y #32) se implementaron como bridges en Kotlin encapsulados en un módulo nativo propio.

---

## Consecuencias

**Positivas:**
- Curva de aprendizaje mínima — el equipo arrancó productivo desde el primer sprint
- Expo Go acelera el ciclo de feedback durante el desarrollo (sin compilar) para las partes que no dependen de módulos nativos

**Negativas / limitaciones:**
- La carpeta `android/` está commiteada en el repositorio (a partir del PR #106), lo que significa que `expo prebuild` ya no puede regenerarla y los servicios nativos no funcionan en Expo Go. Cualquier cambio en la configuración nativa requiere editar directamente los ficheros de Gradle y el `AndroidManifest.xml`.
- El modo Sénior con protección automática (interceptación de llamadas y notificaciones) es exclusivo de Android. En iOS, el sistema operativo no permite a apps de terceros acceder a llamadas entrantes ni leer notificaciones de otras apps.
- El JavaScript bridge introduce latencia en operaciones de alto rendimiento (no relevante para este caso de uso)
- Los módulos nativos (`CallScreeningService`, `NotificationListenerService`) necesitan mantenimiento separado cuando Android actualiza sus APIs de accesibilidad

---

## Estado de implementación

La decisión está implementada en el MVP. La app móvil está construida íntegramente en React Native con Expo SDK 58. Los módulos nativos de accesibilidad están implementados como PoC en las issues #31 y #32.
