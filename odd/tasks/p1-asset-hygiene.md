# Feature: p1-asset-hygiene — CSS muerto + cache-busting de compuesto_cascade.js

Status: DONE — commit 590e09d en origin/main (e2e0cba fue el hash pre-rebase;
la versión final pusheada es 590e09d), desplegado en producción.

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

- [x] T1 Limpieza CSS muerto + comentario de sección 2 alineado con realidad
      (familias = solo chips). Mantener paleta --pt-c/t-metales y
      --pt-c/t-no-metales (los chips de familia la reusan).
- [x] T2 Cache-busting compuesto_cascade.js: `?v=1` en compuesto_form.html.
- [x] T3 Tests: (a) CSS sin selectores muertos (match acotado por límite de
      token: '.pt-celda-metales' no es 'pt-celda-metales-de-transicion', sobre
      CSS sin comentarios) + chips de familia presentes + guard renderizado
      (ninguna celda con slug de familia, regex con lookahead);
      (b) test "compuesto_cascade.js?v=1" en compuesto_form.html.
- [x] T4 Suite completa verde (300 passed, era 297) + manage.py check limpio
      + work-unit commit 590e09d (chore, en origin/main). Desplegado en
      producción (commit e2e0cba era el hash previo a un rebase; el cambio
      final pusheado es 590e09d, mismo árbol).

## Evidence

- periodic_table.css: reglas duales .pt-celda+N.pt-chip de familia
  reducidas a .pt-chip (T1); comentario sección 2 explica por qué no hay
  celdas de familia; comentario de chips de familia actualizado.
- compuesto_form.html L146: script ?v=1.
- app_quimico/tests/test_elemento_lista_vistas.py: +2 tests
  (test_css_no_conserva_celdas_de_familia,
  test_ningun_celda_lleva_slug_de_familia).
- app_quimico/tests/test_compuesto_smiles.py: +1 test
  (test_form_template_cache_busts_the_cascade_script).
- FIXED durante T3: substring matches falsos ('pt-celda-metales' es
  substring de 'pt-celda-metales-de-transicion' en CSS y HTML renderizado)
  → regex con límite de token (?![\w-]); comentario del CSS mención
  literal del selector muerto → evaluar CSS sin comentarios.
