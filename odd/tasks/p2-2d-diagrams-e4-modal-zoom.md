(completa a medida que se ejecutan)

## Evidence

- T1: doc sellado por el operador (2026-09-26); mirror Engram id 585 y
  proyección todo completados 2026-09-27.
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
  `makemigrations --check --dry-run` sin cambios. Work-unit commit con
  Conventional Commit en español (ver git log).
