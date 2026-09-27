# Feature: p1-periodic-table-e2 — Tabla periódica dinámica (Entrega 2, niceties)

Continuación de p1-periodic-table (Entrega 1, COMPLETA y en producción).
Alcance sellado en Engram obs #527 (rev 3): niceties de la vista tabla.
Decisiones del operador (2026-09-28): detail card flotante al hover/focus con
datos básicos; animación staggered por Z; preferencia de vista con
localStorage + URL explícita (funda el bug reportado: volviendo desde el
detalle de un elemento siempre se caía a tarjetas).

## Scope (Entrega 2)

- **View preference**: la última vista elegida se guarda en localStorage;
  el link "Volver al listado" desde el detalle (y cualquier entrada sin
  `?vista=`) abre en la vista recordada. Un `?vista=` explícito en la URL
  gana SIEMPRE sobre localStorage (links/bookmarks deterministas).
- **Hover/detail card**: tarjeta flotante al hover (y al focus de teclado)
  de una celda, con símbolo, nombre, Z, categoría, grupo/período y peso.
  Datos ya presentes en data-*/plantilla: cero peticiones al servidor.
- **Search highlight**: la búsqueda existente no solo atenúa: las celdas
  que matchean resaltan visualmente el símbolo/nombre (estado `.pt-match`
  ya existe a medias via `pt-destacada`; E2 agrega resaltado del texto).
- **Keyboard nav + ARIA**: navegación con flechas entre celdas de la grilla
  (121 celdas, incluidas las 2 filas f despegadas), ARIA labels por celda,
  respetando que ya son `<a>` (focusable nativo).
- **Staggered entrance**: animación de entrada con delay proporcional a Z
  ("se llena la tabla"); respeta `prefers-reduced-motion`; solo en la
  primera visita de la sesión (sessionStorage) para no molestar en cada
  recarga.

Rechazado (sellado en #527, se mantiene): pan/zoom drag, filtros por rango
de período, librerías de terceros, hover zoom.

## Restricciones de convención (obs #592/#593/#594)

- Commits por unidad dentro de la entrega: `(Tn de E2 p1-periodic-table-e2)`.
- Push/deploy/validación: PREGUNTAR al operador en cada transición; toda
  nota transitoria del doc lleva fecha y dueño de la decisión.
- Pendientes del reporte: verificados contra origin/main y README.

## Tasks

- [ ] T1 Feature doc + todo projection + Engram mirror (este doc)
- [x] T2 View preference: localStorage "gestorQuimicoVistaElementos" +
      fallback en template cuando GET no trae vista; JS en los botones de
      toggle; URL explícita intacta; tests (GET ?vista gana; sin GET cae al
      default del servidor — la preferencia la aplica el cliente; guard de
      valor inválido en localStorage).
      Implementado por gentle-ai-worker (RED 3 failed → GREEN 38 passed
      módulo, era 32; manage.py check limpio). Verificación independiente
      gentle-ai-verify: PASS 5/5 checks. Commit 4851d94 (parent).
      FIX de feedback del operador (81c23c9): el comentario {# #} del guard
      en 3 líneas se filtraba al HTML (los comentarios Django solo abarcan
      una línea, misma clase que e64f753) — movido a comentario JS dentro
      del script + test anti-regresión generalizado: ningún {#/#} filtrado
      en ninguna vista (tests 38→39).
- [x] T3 Detail card: partial template de la card (datos: Z, símbolo,
      nombre, categoría, grupo/período, peso; NULL honesto), markup en las
      celdas (data-* ya existen; agregar data-grupo/data-periodo), CSS de
      la card flotante correcta en ambos temas, JS hover/focus/focusout con
      posicionamiento acotado a viewport, tests de markup y clases.
      Implementado por gentle-ai-worker (RED 12 intended failures → GREEN
      50 passed módulo, era 39; labels honestos: Po [209] = 'Número másico').
      Feedback del operador corregido en 50c47de + adaa93c: cabecera
      'Z=57 [La] Lantano' (rótulo Z=, símbolo entre corchetes cuadrados,
      data-*-display canónicos IUPAC — sin text-transform), peso con coma
      decimal, y separación vertical del detalle en móvil (styles.css
      ?v=5, .detalle-elemento-simbolo). Sin 'Ver detalle' (3ccdfc5): la
      celda entera es el enlace y el texto era affordance falsa (decisión
      del operador: card = resumen puro).
      Verificación independiente gentle-ai-verify: PASS 6/6 checks. Commit
      23fdb4c (parent).
- [x] T4 Keyboard nav + ARIA: roving tabindex con flechas (±1 col, ±1 fila)
      sobre las celdas de la grilla, aria-label descriptivo por celda
      ("Fe, hierro, Z 26, metal de transición"), test del markup.
      Implementado por gentle-ai-worker (RED 8 failed → GREEN 57 passed).
      Verificación independiente gentle-ai-verify: PASS 6/6. Commit 23873d0.
      Realización final distinta al ejemplo del plan: label canónico
      "La — Lantano, número atómico 57, Lantánidos" (símbolo IUPAC
      visible primero, WCAG 2.5.3).
- [x] T5 Search highlight: subrayado/resaltado dentro de la celda cuando
      hay búsqueda activa y matchea (span .pt-match en símbolo y nombre),
      test de clase en markup + JS toggling.
      Implementado por gentle-ai-worker (mark.pt-resaltado, no .pt-match —
      normalizarConMapa mapea índices normalizado→original: 'hidro'
      resalta 'Hidró' con acento; aria/data-* intactos; guard anti-rebuild
      en hover). Verify PASS 6/6. Commit 143e2ed; tests 57 → 66.
- [x] T6 Staggered entrance: @keyframes entrada + animation-delay por Z
      (inline en template), prefers-reduced-motion desactiva, sessionStorage
      "pt-animada" evita repetir en la misma sesión; CSS/JS ?v= bump;
      tests de CSS (keyframes, reduced-motion) y del flag.
      Implementado por gentle-ai-worker (delay calc((var(--pt-z) - 1) *
      12ms); sessionStorage ptEntradaAnimada una vez por tab; fail-safe en
      read/write; fill-mode backwards; cleanup 1804ms). Verify PASS 6/6.
      Commit c5f2593; tests 66 → 74.
- [x] T7 Suite completa verde + manage.py check + makemigrations --check
      (sin cambios de modelos: E2 es frontend-mostly) + cache-bust ?v=
      correcto en elemento_lista.html.
      Cerrada 2026-09-28: check limpio (0 issues) y makemigrations --check
      'No changes detected'. Suite por módulos touched-adjacent: 94 passed
      módulos elementos+detalle+cargar_elementos + 2 cache-bust tests
      ajustados ?v=4 -> ?v=5 verdes (commit fdc517a). Full suite local
      quedo en ruido transitorio MySQL por aborts (18F/289P/105E, patrón
      obs #585, no del código) — decisión del operador: no exigir full
      suite local, el CI de GitHub corre el full suite en el push. Working
      tree limpio tras fdc517a.
- [ ] T8
2026-09-28: main local 16 commits ahead de origin/main (sin pushear,
      push sale en T8 con decisión del operador). Pendientes: Validación local del operador → decidir push (preguntar) → CI
      verde → deploy PA (pull + collectstatic + Reload; venv
      ~/.virtualenvs/gestor) → validación en producción → cierre de notas
      con estados datados.

## Operator feedback (validación T8, 2026-09-28)

- [x] F1 fix resaltado pegado (T5): el guard de limpiarResaltado comparaba
      textContent con el texto original; un <mark> que envuelve todo el
      texto deja el textContent idéntico al original y nunca se limpiaba
      (solo F5 lo sacaba). Reproducido en Node+jsdom con la secuencia
      H -> borrar -> A -> borrar antes del fix. Detección por NODO
      (querySelector('mark')). Commit 4315013; JS ?v=9; tests 74 -> 75.
- [x] F2 opción (b) entrada escalonada (T6): recarga completa (F5,
      type 'reload') re-anima ignorando el flag; navegación interna sigue
      sin repetir. Mismo commit 4315013 (verificado en jsdom: primera
      visita anima, vuelta interna no, F5 con flag anima).
- [x] F3 revalidación del operador (2026-09-28): T5 (secuencia H -> A ->
      limpiar sin residuos) y T6 (F5 re-anima) pasaron; validación local
      10/10. Pendiente decisión de push (T8 continúa).

## Decisions

- Card flotante con datos básicos (NO con electronegatividad/radio): el
  hover es un peek, el detalle completo ya existe en su página.
- Animación: opción (b) del operador — recarga completa (F5) re-anima; navegación interna no (flag por pestaña).
- localStorage solo como default; `?vista=` explícito siempre gana.

## Evidence

(completa a medida que se ejecutan)

## Next step

T2 (después de T1 ya hecha con este write).
