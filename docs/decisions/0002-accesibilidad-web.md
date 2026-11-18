# ADR 0002: Decisiones de accesibilidad e inclusividad — Portal web

**Fecha:** 2026-11-18  
**Estado:** Aceptado  
**Autora:** Majo

---

## Contexto

El portal web de Avizor está dirigido a Tutores (familiares de personas mayores). El producto debe ser usable por personas con diversidad funcional: neurodivergencias, discalculia, fotosensibilidad, baja visión o quienes usan productos de apoyo como lectores de pantalla.

---

## Decisiones tomadas

### 1. Tipografía sin serifa + interlineado amplio
**Decisión:** `Inter` como fuente principal, `line-height: 1.6–1.7` en todo el CSS.  
**Por qué:** Las fuentes sin serifa reducen la carga cognitiva. El interlineado amplio facilita la lectura a personas con dislexia.

### 2. Sin emojis como metáforas
**Decisión:** Cero emojis en la UI. Se usan iconos Lucide con `aria-hidden="true"` y etiqueta de texto visible junto a ellos.  
**Por qué:** Los emojis son ambiguos para personas con discapacidad cognitiva o para lectores de pantalla. Un icono con texto siempre es más claro.

### 3. Lenguaje sencillo
**Decisión:** Todos los textos revisados para evitar tecnicismos.  
**Por qué:** El portal lo usa población general, no técnica. Frases cortas, vocabulario cotidiano.

### 4. Sin CTAs de presión
**Decisión:** No hay mensajes de urgencia ("¡Compra ahora!", "Quedan 3 plazas").  
**Por qué:** Generan estrés y pueden dificultar la toma de decisiones en personas con ansiedad o neurodivergencias.

### 5. Modo lectura automático (prefers-color-scheme)
**Decisión:** Cuando el SO está en modo oscuro, el portal activa una paleta cálida sepia (`#f5f0e8`) en vez de un fondo negro.  
**Por qué:** El fondo crema reduce el efecto de vibración del blanco puro, recomendado para dislexia. El modo oscuro estándar (negro puro) puede ser demasiado contrastado para personas con fotosensibilidad.

### 6. Respeto al movimiento reducido (prefers-reduced-motion)
**Decisión:** Todas las animaciones y transiciones se desactivan si el usuario tiene configurado `prefers-reduced-motion: reduce` en su SO.  
**Por qué:** Las animaciones pueden causar malestar físico en personas con vértigo, epilepsia fotosensible o ciertas neurodivergencias.

### 7. Scroll suave condicional
**Decisión:** `scroll-behavior: smooth` solo se aplica si `prefers-reduced-motion: no-preference`.  
**Por qué:** El scroll animado puede ser confuso o causar malestar. El comportamiento nativo del navegador es siempre más predecible.

### 8. Focus visible para navegación por teclado
**Decisión:** Anillo de foco visible (`:focus-visible`) en todos los elementos interactivos.  
**Por qué:** Usuarios que navegan con teclado (movilidad reducida, lectores de pantalla) necesitan saber en todo momento dónde está el foco.

### 9. Toggle de contraseña visible
**Decisión:** Botón de ojo en todos los campos de contraseña (login y registro).  
**Por qué:** Personas con dislexia o memoria de trabajo reducida se benefician de poder ver lo que escriben. Copiar y pegar tampoco está deshabilitado.

### 10. aria-live en contenido dinámico
**Decisión:** `aria-live="polite" aria-atomic="true"` en errores de formulario, confirmaciones, estado de carga, contadores del panel de analítica, el código de vinculación y su cuenta atrás.  
**Por qué:** Los cambios dinámicos en pantalla son invisibles para lectores de pantalla si no se anuncian explícitamente.  
**Aplica a:** `analytics.html` (#total-count, #fetch-error), `panel.html` (#summary-total, #panel-loading, #pairing-code-display, #pairing-countdown), formularios de login y registro.

### 11. Labels siempre visibles, no solo placeholder
**Decisión:** Todos los inputs tienen `<label>` visible encima del campo.  
**Por qué:** El placeholder desaparece al escribir, lo que puede desorientar a personas con memoria de trabajo reducida.

### 12. Formularios simples y espaciados
**Decisión:** Login y registro con un campo por línea, espaciado generoso, botón con mensaje de acción claro ("Crear cuenta", "Iniciar sesión").  
**Por qué:** Los formularios densos aumentan la carga cognitiva. Un botón con verbo de acción claro reduce la incertidumbre.

### 13. min-height en vez de height fija en contenedores de gráficas
**Decisión:** `.chart-wrap` usa `min-height: 300px` en vez de `height: 300px`.  
**Por qué:** Si el usuario aumenta el tamaño de fuente del navegador, los contenedores con altura fija pueden recortar el contenido.

### 14. HTML semántico
**Decisión:** Uso de `<nav>`, `<main>`, `<section>`, `<footer>`, `<h1>`–`<h3>` en orden correcto. Las pestañas de soporte usan `role="tablist"`, `role="tab"` y `role="tabpanel"` con `aria-selected`.  
**Por qué:** Los productos de apoyo (lectores de pantalla, navegación por voz) dependen de la estructura semántica para funcionar correctamente.

### 15. Listas numeradas con posicionamiento absoluto (no grid)
**Decisión:** Los pasos de la guía del Tutor (`.steps li`) usan `position: relative` + `::before` con `position: absolute` en lugar de `display: grid`.  
**Por qué:** Con `display: grid` en un `<li>`, los navegadores pueden tratar los nodos de texto y los elementos inline (`<strong>`) como ítems de grid separados, rompiendo el layout. El posicionamiento absoluto del número es siempre predecible independientemente del contenido inline del paso.

### 17. Perfil de accesibilidad del Sénior
**Decisión:** Al crear un código de vinculación, el Tutor puede indicar las condiciones del Sénior: daltonismo, baja visión, ceguera e hipoacusia. El perfil se guarda en el backend y se devuelve al dispositivo Sénior al canjear el código, donde se persiste en SecureStore y se aplica globalmente via `AccessibilityContext`.  
**Por qué:** Las adaptaciones deben estar disponibles desde el primer uso sin que el Sénior tenga que configurar nada. El Tutor, que conoce las necesidades del familiar, es quien lo configura durante el proceso de vinculación.  
**Adaptaciones aplicadas:**
- `largeText` (baja visión o ceguera): aumenta el tamaño de fuente en inputs, tabs, botones, mensajes de error y pantallas de bloqueo
- `colorBlind` (daltonismo): añade etiqueta de texto SEGURO / SOSPECHOSO / PELIGRO junto al indicador de color en el resultado del análisis y en la pantalla de bloqueo
- `hardOfHearing` (hipoacusia): reservado — pendiente de implementación (ver issue abierto)  
**Recogida del perfil en:** `PairingScreen` (mobile), `panel.html` (web), paso 2 de `register.html` (web).

### 16. Separación de contenido público y autenticado
**Decisión:** Las páginas con datos personales (analítica por usuario, panel del Tutor) están detrás de autenticación. La landing pública no incluye links a esas secciones ni en el navbar ni en los accesos rápidos.  
**Por qué:** Mostrar datos de protección a usuarios no autenticados no tiene sentido y podría exponer información privada. Además, reduce la carga cognitiva de la landing: los usuarios anónimos ven solo información sobre el producto.

---

## Pendiente

| Decisión | Prioridad | Notas |
|----------|-----------|-------|
| Toggle manual de modo lectura en la UI | Media | Ahora solo se activa si el SO está en modo oscuro |
| Toggle manual de modo calma (animaciones) | Media | Ahora solo se activa con `prefers-reduced-motion` del SO |
| Testing con NVDA (lector de pantalla Windows) | Alta | Probar navegación por teclado en landing, login, registro y panel |
| Documentar resultado del testing con NVDA | Alta | Añadir hallazgos a este ADR |
| Adaptaciones para hipoacusia (`hardOfHearing`) | Alta | Vibración reforzada en notificaciones push y animación de alerta en BlockScreen cuando `hearing_impairment = true` |

---

## Testing recomendado

**Herramienta:** NVDA (gratuito) — [nvaccess.org](https://www.nvaccess.org)  
**Activar:** `Ctrl + Alt + N`

**Checklist mínimo:**

**Landing pública (`/`)**
1. Navegar la página completa solo con `Tab` y `Enter`
2. Verificar que el foco es visible en todo momento
3. Comprobar que los iconos no se leen como texto extraño

**Autenticación (`/login`, `/register`)**
4. Comprobar que los errores de formulario se anuncian al aparecer
5. Verificar que el toggle de contraseña anuncia "Mostrar/Ocultar contraseña"

**Panel del Tutor (`/panel`)**
6. Verificar que "Cargando tu panel…" se anuncia al entrar
7. Comprobar que el contador de ataques detectados se anuncia al cargar
8. Verificar que el código de vinculación y la cuenta atrás se anuncian correctamente

**Soporte (`/support`)**
9. Verificar que las pestañas de soporte funcionan con teclado (Tab + Enter)
10. Comprobar que los pasos numerados se leen en orden correcto
