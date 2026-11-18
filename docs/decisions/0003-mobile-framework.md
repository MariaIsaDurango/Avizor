# ADR 0003: React Native (Expo) como framework móvil

**Fecha:** 2026-11-18  
**Estado:** Aceptado  
**Autora:** Majo

---

## Contexto

Avizor necesita una app móvil cross-platform (iOS y Android) con dos modos diferenciados: Tutor y Sénior. El modo Sénior requiere acceso a servicios nativos de accesibilidad de Android (`AccessibilityService` para interceptar llamadas y notificaciones). El equipo tiene experiencia previa en TypeScript/JavaScript y el panel web ya está desarrollado en ese stack.

Las opciones evaluadas fueron React Native con Expo y Flutter.

---

## Alternativas consideradas

### React Native con Expo (development build)
- Mismo lenguaje que el resto del proyecto (TypeScript)
- Expo Go permite probar en dispositivo sin compilar durante el desarrollo
- El desarrollo build permite añadir módulos nativos cuando Expo SDK no es suficiente
- Compartición de tipos y contratos con el backend sin fricción
- Ecosistema maduro con librerías para todo lo que necesita el proyecto (`expo-notifications`, `expo-secure-store`, `expo-haptics`, `@react-navigation`)

### Flutter
- Rendimiento de renderizado superior (motor Skia/Impeller propio)
- Consistencia visual perfecta entre plataformas
- Requiere aprender Dart — lenguaje que nadie del equipo conocía
- Mayor fricción para compartir tipos con el backend TypeScript
- Ecosistema de librerías de accesibilidad nativa menos maduro en el momento de la decisión

---

## Decisión

**React Native con Expo (development build).**

El factor determinante fue la velocidad de desarrollo: el equipo domina TypeScript, el panel web y la app móvil comparten los mismos contratos de API, y Expo proporciona prácticamente todas las librerías necesarias sin configuración nativa adicional. El módulo nativo de `AccessibilityService` (PoC #31 y #32) se implementó como un bridge Java/Kotlin encapsulado, sin necesidad de abandonar el stack Expo.

---

## Consecuencias

**Positivas:**
- Curva de aprendizaje mínima — el equipo arrancó productivo desde el primer sprint
- Expo Go acelera el ciclo de feedback durante el desarrollo (sin compilar)
- Tipos compartidos con el backend eliminan errores de integración

**Negativas / limitaciones:**
- El JavaScript bridge introduce latencia en operaciones de alto rendimiento (no relevante para este caso de uso)
- El production build requiere EAS Build o entorno nativo configurado — no es suficiente con Expo Go
- Los módulos nativos (`AccessibilityService`, `CallScreeningService`) necesitan mantenimiento separado cuando Android actualiza sus APIs de accesibilidad

---

## Estado de implementación

La decisión está en producción. La app móvil está construida íntegramente en React Native con Expo SDK 58. Los módulos nativos de accesibilidad están implementados como PoC en las issues #31 y #32.
