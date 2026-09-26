# Feature: p2-2d-diagrams-e4-modal-zoom — Diagrama 2D ampliado en modal

Sealed design (2026-09-26, propuesto por el operador durante la validación
de la Entrega 3): la miniatura del diagrama en tarjetas/detalle es chica
por espacio; un modal de Bootstrap re-dibuja el mismo SMILES a tamaño
grande (SVG nítido, no estiramiento). Entrega 1..3 permanecen intactas.

Comportamiento sellado:
- Las tarjetas siguen mostrando su diagrama miniatura tal cual hoy.
- Click sobre el diagrama abre el modal (cursor zoom-in como pista) +
  botón "Ampliar" visible junto al diagrama (accesibilidad).
- El modal re-renderiza el SVG a ≈600×450 con el mismo SMILES (nítido,
  no estiramiento de imagen); mismo fondo claro fijo (legible en ambos
  temas, decisión de la Entrega 1).
- Cierre: X, ESC, click fuera (modal nativo BS5, cero JS custom de modal).
- Solo para compuestos con SMILES: sin estructura, todo queda igual.
- En lista Y detalle.
- Caveat a documentar (observación del operador con K4[Fe(CN)6]):
  SmilesDrawer dibuja por símbolo elemental — el carbono de un ligando
  cianuro se ve como un C orgánico corriente (correcto: es un carbono
  con valencia cumplida); si el SMILES trae [C-]#N con carga, el drawer
  muestra la etiqueta de carga.

Non-goals: zoom/pan con rueda o arrastre (descartado en Entrega 1),
descarga de imagen, tamaño configurable por el usuario.

## Tasks

- [x] T1 Feature doc + Engram mirror + todo projection (este doc)
      (mirror Engram id 585; nota: una escritura accidental pisó la
      sección superior de este doc y fue reconstruida desde el commit
      cca5065, 2026-09-27)
- [x] T2 JS: re-dibujo en el modal (aprovechar el core de smiles_render.js)
      + tests (aserciones de función/contrato)
- [x] T3 Templates: tarjeta y detalle ganan disparador (click + botón)
      + modal base + tests de plantilla
- [x] T4 Suite completa verde + work-unit commit (español)
      (367 passed, era 328; check y makemigrations --check limpios;
      commit c02bcd6)
- [ ] T5 Validación local operador → push → PA (collectstatic + Reload)
      → validación producción
      (validación local OK, 10/10, operador 2026-09-27; push a
      origin/main hecho; falta deploy PA y validación producción)

## Evidence

(completa a medida que se ejecutan)

- T2: `static/js/smiles_render.js` refactor conservador — core
  `dibujarSvg(smiles, width, height) -> svg|null` extraído de `renderOne`
  (mismo fail-soft), nuevo flujo modal-zoom `abrirModalZoom` con
  `bootstrap.Modal.getOrCreateInstance(modal).show()` (ciclo 100% nativo
  BS5, sin close custom), dibujo a 600x450 reutilizando
  `centrarContenido`, listeners delegados de click y keydown
  (Enter/Espacio sobre el contenedor tabindex=0; el botón nativo ya
  emite click). Guard `typeof SmilesDrawer === "undefined"` intacto; el
  wiring del modal es independiente de SmilesDrawer (sin librería, el
  modal abre y muestra aviso fail-soft "No se pudo generar la estructura
  2D."). El modal se muestra ANTES de dibujar: getBBox en nodo
  display:none da caja vacía. `node --check` OK.
- T3: compuesto_lista.html — `.estructura-2d` gana
  `data-smiles-zoom tabindex="0" role="button"` + botón
  `🔍 Ampliar` (`data-smiles-ampliar="{{...smiles_para_render}}"`); UN
  modal compartido (`id="modal-estructura-2d"`, modal-dialog modal-lg
  centered, aria-labelledby, body `estructura-2d-modal` con
  `data-smiles-modal-body`) emitido UNA vez fuera del grid con
  `{% for %}{% if compuesto.smiles %}{% ifchanged %}` (comparado contra
  el último valor VISTO, no contra la iteración anterior; en iteraciones
  sin SMILES el tag no se evalúa y no resetea). compuesto_detalle.html —
  mismo patrón en el tab-pane #estructura2d, modal dentro del guard
  `{% if compuesto.smiles %}`. styles.css: `cursor: zoom-in` en
  `.estructura-2d`; `.estructura-2d-modal` fondo `#ffffff` fijo + svg
  `width:100%; height:auto; max-width:600px` (nítido, sin estiramiento);
  `.estructura-2d-modal__aviso`. Cache-bust: smiles_render.js `?v=3`
  en ambos templates; styles.css `?v=4` en base.html.
- Tests: nuevo `app_quimico/tests/test_smiles_modal_zoom.py` (17 tests
  de contrato: fuente JS, HTML renderizado lista/detalle, unicidad del
  modal, ausencia sin SMILES, cache-busts, CSS) + asserts viejos de
  cache-bust actualizados en test_compuesto_smiles.py (?v=2→3, ?v=3→4).
- T4: suite completa `.venv/Scripts/python.exe -m pytest -q` →
  **367 passed** (era 328 tras Entrega 3). `manage.py check` limpio;
  `makemigrations --check --dry-run` sin cambios. Anomalía ambiental
  transitoria documentada: una corrida completa previa reportó errores
  de conexión a MySQL de test (lock/conexiones tras el abort de un
  subagente en la misma sesión); no reproducible y ajenos al cambio.
  Work-unit commit: `c02bcd6`.
- T5 (parcial): validación local del operador OK (10/10: click, botón
  Ampliar, cierre X/ESC/click fuera, nítido) 2026-09-27; push
  `0e09629..c02bcd6` a origin/main; RDD off en este clone, entrega por
  política ordinaria.
