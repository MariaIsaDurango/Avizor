# ADR 0001: React Navigation sobre Expo Router

**Fecha:** 2026-11-07  
**Estado:** Aceptado

## Contexto

La app móvil de Avizor usa Expo (SDK 58) con TypeScript. Había que elegir una solución de navegación entre las dos opciones principales del ecosistema.

## Decisión

Usamos **React Navigation** (`@react-navigation/native` + `@react-navigation/native-stack`).

## Razones

- El template `blank-typescript` no incluye Expo Router — añadirlo requeriría refactorizar la estructura de entrada (`index.ts` → `app/`)
- React Navigation es más maduro, con mayor documentación y comunidad
- El árbol de navegación de Avizor (modo Sénior / modo Tutor, con rutas condicionadas por rol) se beneficia de un control explícito, no de enrutamiento basado en sistema de archivos
- Expo Router está optimizado para apps con estructura similar a web (URLs compartibles), que no es el caso de Avizor

## Consecuencias

- Las rutas se definen explícitamente en `src/navigation/RootNavigator.tsx`
- Los tipos del árbol de navegación están en `src/navigation/types.ts`
- No usar el directorio `app/` como convención de rutas
