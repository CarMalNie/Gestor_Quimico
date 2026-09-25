# Feature: p1-asset-hygiene — CSS muerto + cache-busting de compuesto_cascade.js

Status: IN PROGRESS (backlog punto 1 de la sesión 2026-09-25, post-cierre
p1-categoria-filtros + p2-2d-diagrams Entrega 1)

## Scope

Mini-feature de higiene front-end, sin cambios de comportamiento visible
salvo invalidación de caché.

1. Limpiar CSS muerto de `static/css/periodic_table.css`: `.pt-celda-metales`
   y `.pt-celda-no-metales` son selectores muertos (las familias son solo
   chips, nunca celdas de la grilla) — quedan como parte de reglas duales con
   `.pt-chip-metales`/`.pt-chip-no-metales` (esas SÍ se usan). Ajustar el
   comentario de la sección 2 que aún describe el mapeo dual como si toda
   pareja celda+chip existiera.
2. Cache-busting: `compuesto_form.html` incluye `compuesto_cascade.js` sin
   versión → agregar `?v=1`, patrón idéntico a los otros 3 assets versionados
   (periodic_table.css ?v=4, periodic_table.js ?v=3, smiles_render.js ?v=2,
   styles.css ?v=3).

Non-goals: sin renombres de datos, sin cambios de models/vistas, sin
touch -> behavior.

## Tasks

- [ ] T1 Limpieza CSS muerto + comentario de sección 2 alineado con realidad
      (familias = solo chips). Mantener paleta --pt-c/t-metales y
      --pt-c/t-no-metales (los chips de familia la reusan).
- [ ] T2 Cache-busting compuesto_cascade.js: `?v=1` en compuesto_form.html.
- [ ] T3 Tests: (a) afirmar que la plantilla tabla no emite celdas con slug
      de familia / que el CSS ya no tiene `.pt-celda-metales` ni
      `.pt-celda-no-metales` muertos SOLO si se pueden formular de forma
      estable — preferir test directo sobre el CSS (selectores muertos fuera)
      + test de chips de familia presentes; (b) test de cache-busting de
      compuesto_cascade.js análogo al de smiles_render.js (?v=1 en form).
- [ ] T4 Suite completa verde + work-unit commit (Conventional Commit).
      Push/deploy: solo con pedido explícito del operador.

## Evidence

(completa a medida que se ejecutan)
