# Feature: p1-periodic-table — Tabla periódica dinámica (Entrega 1)

Frontend-mostly feature: view toggle between card list and periodic-table
CSS grid, interactive category legend, honesty styling for synthetic
elements, dark-mode correctness. Design sealed in Engram obs #527
(rev 3, includes agreed filter semantics for the table view).

## Scope (Entrega 1)

- View toggle card list <-> periodic-table grid (coexist; cards view keeps
  exact current server-side filtering and rendering).
- Table view: all 118 elements rendered from DB; client-side filters
  (dim/attenuate semantics, no cells removed).
- Interactive category legend chips: hover/click -> highlight that category,
  dim the rest (replaces the server-side categoria select in table view).
- Search input: symbol/name highlight (client-side vs `busqueda_nombre`).
- `min_peso_atomico`: numeric threshold keeping full opacity for
  peso_atomico >= threshold, dims the rest. All AND-combined.
- Honesty styling: 15 synthetic elements (Z >= 104) as visually distinct
  cells (data is theoretical).
- Dark mode correct in both `data-bs-theme` modes (CSS custom properties).

Rejected (sealed): pan/zoom drag, period-range filters, third-party
periodic-table libraries. Vanilla JS + own CSS Grid. localStorage view
preference, hover zoom, keyboard nav/ARIA and entrance animation are
Entrega 2.

## Tasks

- [ ] T1 Feature doc + todo projection + Engram mirror + plan (this doc)
- [x] T2 Backend: ElementoListView accepts `vista=tabla|tarjetas` (default
      tarjetas = untouched current behavior). In tabla mode: full
      118-element queryset (no server-side filtering; filters apply
      client-side), context adds CATEGORIA_CHOICES for legend rendering.
      Tests (pytest): default view identical to today; tabla mode returns
      118 elements ordered by Z; tabla ignores GET filter params server-side.
      + Evidence: app_quimico/views.py `ElementoListView` (get_vista
        normalizes unknown values to tarjetas; context adds `vista` and
        `categorias` from `CATEGORIA_CHOICES`; tabla queryset = all 118 with
        select_related, no server-side filters).
      + Evidence: app_quimico/tests/test_elemento_lista_vistas.py (8 tests).
      + Checks: `pytest -q` -> 168 passed (160 baseline + 8 new);
        `manage.py check` -> no issues. Commit: pending (parent owns commit).
- [x] T3 Template: elemento_lista.html toggle buttons (cards/grid) + grid
      markup (CSS grid 18 cols x 7 rows + 2 detached f-block rows for
      Ce..Lu / Th..Lr; La/Ac stay at (P6,G3)/(P7,G3) per stored data) +
      legend chip row + client-side filter controls (search, peso
      threshold). Grid cell: Z, symbol, name; links to elemento_detalle.
      Cards branch byte-identical to current markup.
      + Evidence: app_quimico/templates/.../elemento_lista.html (toggle
        btn-group with `?vista=` links + active state; tabla branch: chip row
        `#pt-leyenda` with 12 `button.pt-chip[data-categoria]` from
        `categorias`, `#pt-buscar` search, `#pt-peso-min` number input, no
        server form; grid `#pt-tabla.pt-grid` with one
        `a.pt-celda.pt-celda-<slug>[data-categoria][data-simbolo][data-nombre]`
        per element, inline `grid-column/grid-row`, `pt-sintetico` for Z>=104,
        `pt-fila-f` for the detached rows; tarjetas branch keeps the exact
        filter card + cards grid).
      + Evidence: app_quimico/views.py `ElementoListView` (`PosicionTabla`
        namedtuple + `_posicion_celda`/`_posiciones_tabla` helpers; context
        adds `posiciones_tabla` (dict keyed by symbol) only in tabla mode).
      + Evidence: app_quimico/tests/test_elemento_lista_vistas.py (7 new tests:
        f-block/detached rows, main-grid positions, no collisions, tabla-only
        context key, element without DetalleElemento, grid+legend+client
        filter markup, cards keeps the server form) -> 15 tests in the file.
      + Checks: `pytest -q` -> 175 passed (168 baseline + 7 new);
        `manage.py check` -> no issues. Live render on the dev DB (118 rows):
        rows 1-7 + 9 + 10, lanthanides row 9 cols 4..17 (Ce..Lu), actinides
        row 10 cols 4..17 (Th..Lr), 12 chips, 15 `pt-sintetico` cells.
        Commit: pending (parent owns commit).
- [x] T4 CSS: static/css/periodic_table.css — category color map for all 12
      CATEGORIA_CHOICES via CSS custom properties, [data-bs-theme="light"|"dark"]
      variants, honesty styling class (dashed/muted) for Z>=104,
      .pt-dim/.pt-highlight state classes, responsive fallback (scroll or
      reduced cells on small screens; readable >= lg).
      Naming deviation: the highlight state class is `.pt-destacada` (the T4
      delegation contract named it that way); the T5 JS must use
      `.pt-dim` + `.pt-destacada`.
      + Evidence: static/css/periodic_table.css (Spanish comments, 8 sections:
        palette, category mapping, grid, cell, synthetic honesty, filter
        states, legend/filter bar, responsive). Grid: 18 cols via
        `repeat(18, minmax(0, 1fr))`, explicit 10 rows (7 main + 1 separator +
        2 detached f-block) driven by `--pt-fila`/`--pt-separador`, `gap: 3px`.
        Cell: fixed row height, centered flex column, absolute `--pt-z`
        top-left, bold `--pt-simbolo`, `--pt-nombre` with ellipsis; colors from
        `--pt-bg`/`--pt-fg` mapped per category so cell and chip always match.
        Palette: 12 `--pt-c-<slug>` + 12 `--pt-t-<slug>` pairs, pastel + dark
        text under `[data-bs-theme="light"]` and deep desaturated + light text
        under `[data-bs-theme="dark"]` (no `:root` declaration, so dark mode is
        never overridden). Honesty: `.pt-sintetico` dashed border, saturation
        0.55, italic symbol + `*` superscript, still clickable. States:
        `.pt-dim` (grayscale .7 + opacity .25, no `pointer-events`) and
        `.pt-destacada` (ring + full opacity) composed through `--pt-gris`/
        `--pt-saturacion` so dim/highlight and synthetic saturation never
        overwrite each other; transitions 0.15s ease. Responsive: below lg a
        `minmax(2.6rem, 1fr)` track plus `overflow-x: auto` on the grid gives
        horizontal scroll instead of unusable cells.
      + Evidence: app_quimico/templates/.../elemento_lista.html (stylesheet
        `<link>` at the top of `{% block content %}`; base.html has no
        `extra_css` block and is out of scope, and a body-level stylesheet link
        is valid HTML5). Cards branch markup otherwise unchanged.
      + Checks: `pytest -q` -> 175 passed; focused
        `pytest app_quimico/tests/test_elemento_lista_vistas.py -q` -> 15 passed;
        `manage.py check` -> no issues;
        `manage.py collectstatic --noinput -n --verbosity 2` -> pretends to copy
        `static/css/periodic_table.css`; `manage.py findstatic
        css/periodic_table.css` -> found in `static/`. Live render on the dev DB
        (118 rows): `<link rel="stylesheet" href="/static/css/periodic_table.css">`
        present in both `vista=tabla` and `vista=tarjetas`; 118 `pt-celda`, 15
        `pt-sintetico`, 12 chips. All 12 rendered chip slugs
        (`metales`, `no-metales`, `alcalinos`, `alcalinos-terreos`,
        `lantanidos`, `actinidos`, `metales-de-transicion`, `otros-metales`,
        `metaloides`, `otros-no-metales`, `halogenos`, `gases-nobles`) have a
        matching `.pt-celda-*`/`.pt-chip-*` rule and palette pair.
        Note: the task text's `collectstatic --dryrun` is not a valid Django
        option (it is `-n`/`--dry-run`); the corrected form was used.
        Commit: pending (parent owns commit).
- [x] T5 JS: static/js/periodic_table.js — vanilla-only: legend chip
      hover/click handlers, search input highlight (symbol/name), peso
      threshold dimming; AND-combined classes; no server round-trips.
      + Evidence: static/js/periodic_table.js (IIFE + `readyState` guard; no-op
        unless `#pt-tabla` exists, so tarjetas and other pages are unaffected;
        caches every `.pt-celda` with `data-categoria`/`data-simbolo`/
        `data-nombre`/`data-peso` parsed once; core state
        `{categoria, busqueda, pesoMin}`; `aplicar()` AND-combines the three
        predicates — category equality, case-insensitive symbol/name substring,
        `peso >= threshold` — removing then adding `.pt-dim` when a cell fails
        any active filter and `.pt-destacada` when it passes all; when no filter
        is active every cell is neutral (no classes); cells are never removed;
        chip `click` toggles the active category and syncs
        `aria-pressed="true|false"`; chip `mouseover`/`mouseout` set/reset a
        transient `categoriaPrevia` that overrides the persistent category for
        preview without mutating it (mouseout reverts to the click state);
        `#pt-buscar` `input` -> trim+lowercase; `#pt-peso-min` `input` ->
        `parseFloat` or `null`; repaints batched with `requestAnimationFrame`;
        initial state hydrates from prefilled inputs).
      + Evidence: app_quimico/templates/.../elemento_lista.html (script tag
        `<script src="{% static 'js/periodic_table.js' %}" defer></script>`
        next to the stylesheet include at the top of `{% block content %}`;
        cells gain
        `data-peso="{{ celda.elemento.peso_atomico_elemento|stringformat:'s' }}"`
        so the peso threshold works client-side, rendered as dot-decimal;
        `#pt-peso-min` prefilled with
        `{{ filter_form.min_peso_atomico.value|default_if_none:'' }}`).
      + Checks: `pytest -q` -> 175 passed;
        `manage.py check` -> no issues;
        `manage.py collectstatic --noinput -n --verbosity 2` -> pretends to copy
        `static/js/periodic_table.js`; `manage.py findstatic js/periodic_table.js`
        -> found in `static/`; `node --check static/js/periodic_table.js` -> OK;
        rendered via test client (ALLOWED_HOSTS overridden): `vista=tabla` ->
        status 200, script tag present, 118 `.pt-celda`, 118 `data-peso`
        (samples `1.0080`, `4.0026` — dot decimal, no commas), peso input
        `value=""` by default and `value="50"` with `GET min_peso_atomico=50`;
        `vista=tarjetas` -> no `#pt-tabla` (JS no-op).
        Note: base.html *does* expose `{% block extra_js %}` (the T5 context
        fact was inaccurate); the `<script>` was still placed next to the
        stylesheet as delegated, and base.html is outside the allowed edit
        surfaces. Commit: pending (parent owns commit).
- [x] T6 Full pytest suite green (175 passed) + independent verify PASS
      (all 6 checks, report in session log). Work-unit commits:
      7f97d87 (T2), 9c7dcad (T3), 92b9bbc (T4), b2c347c (T5).
      Local main = 5 commits ahead of origin/main (incl. 5f895a5 gitignore).
      Push + PA deploy (pull + reload + collectstatic — new CSS/JS assets
      REQUIRE collectstatic) pending explicit operator request; then
      production validation in both themes with operator.
- [x] T7 Entrega 1 feedback fixes (operator review of the local render).
      (1) Visible-comment bug: the tabla branch carried a multi-line
      `{# ... #}` block ('Grilla periódica: 18 columnas x 7 períodos' +
      'posiciones_tabla' / 'periodic_table.css'); Django `{# #}` only spans
      one line, so it leaked as literal text. Removed the block entirely
      (the CSS documents itself; the remaining `{# #}` comments in the file
      are all single-line, re-scanned programmatically).
      (2) Header `<h1>` shortened from 'Tabla Periódica: Listado de Elementos'
      to 'Tabla Periódica' (shared by both view modes; Registrar button and
      the rest of the header row untouched).
      (3) Accent-insensitive client search in the tabla view: added a
      `normalizar()` helper (toLowerCase -> NFD -> strip U+0300-U+036F) in
      static/js/periodic_table.js and applied it once to the cached
      `data-simbolo`/`data-nombre` values and to the search term (input
      handler + initial hydration), so 'quimica' matches 'Química',
      'halogenos' matches 'Halógenos'. Click/hover/peso logic unchanged.
      + Evidence: app_quimico/templates/.../elemento_lista.html (comment
        block removed at old lines 60-62; `<h1>` at line 14);
        static/js/periodic_table.js (`normalizar` helper at lines 8-16;
        cache at lines 33-34; search term at lines 131 and 147).
      + Evidence: app_quimico/tests/test_elemento_lista_vistas.py (2 new
        template tests -> 17 tests in the file:
        `test_vista_tabla_no_filtra_comentarios_multilinea_al_html` and
        `test_encabezado_compartido_usa_el_titulo_corto_en_ambas_vistas`).
      + Checks (RED first, then GREEN): focused
        `pytest app_quimico/tests/test_elemento_lista_vistas.py -q` -> 2 failed
        pre-fix (leaked comment present; `h1` old title), 17 passed post-fix;
        full `pytest -q` -> 177 passed (175 baseline + 2 new);
        `manage.py check` -> no issues; `node --check static/js/periodic_table.js`
        -> OK; ad-hoc node normalizer check -> 'Química'->'quimica',
        'Halógenos'->'halogenos', 'Lantánidos'->'lantanidos', 'Símbolo'->'simbolo',
        'Actínidos'->'actinidos' all match; template re-scan -> no multi-line
        `{# #}` comments remain. Commit: pending (parent owns commit).
- [x] T8 UX polish: sticky filter panels on the two list pages (CSS-only +
      minimal wrapper markup; no JS/view logic). New `.filtro-sticky` utility
      in static/css/periodic_table.css section 9 (`position: sticky`,
      `top: var(--filtro-top, 64px)` compensating the fixed navbar ~56px,
      `z-index: 1020` below `.fixed-top` 1030, solid `var(--bs-body-bg)`
      fallback, 1px `--bs-border-color` border, `--bs-border-radius`, bottom
      `box-shadow`). Applied to the filter card in both elemento_lista.html
      branches (tabla card also gets the `pt-filtros-tabla` hook) and to the
      compuesto_lista.html filter card.
      + Deviation: the `.row.mb-4 > .col-12` scaffolding around each filter
        panel was removed and `mb-4` moved onto the panel. Reason:
        `position: sticky` only travels inside its parent's box, and the panel
        was the only child of `.col-12`, so it had zero travel. Net layout
        identical (row negative margins cancel col padding).
      + Deviation: the tabla-mode bar already lived inside a card (the
        delegated context described it as bare), so that card was reused as
        the sticky container instead of nesting a second `.filtro-sticky`
        wrapper (avoids a double frame).
      + Deviation: `.filtro-sticky` declares no padding; `.card-body` already
        provides 1rem and declaring padding here would override it.
      + Note: `background-color`/`box-shadow` in `.filtro-sticky` do not
        override the cards' `bg-body-tertiary`/`shadow-sm` because Bootstrap
        background/shadow utilities use `!important`; the declarations act as
        the solid-background fallback for a panel without utilities.
      + Evidence: static/css/periodic_table.css (section 9, `.filtro-sticky`
        at line 333); elemento_lista.html (tabla card line 40, tarjetas card
        line 78); compuesto_lista.html (filter card line 22).
      + Checks: `pytest -q` -> 177 passed; `manage.py check` -> no issues;
        rendered (test client): `?vista=tabla` -> `filtro-sticky` x1 +
        `pt-filtros-tabla` x1; `?vista=tarjetas` -> x1; `compuestos/`
        (authenticated) -> x1. No test asserts the filter card class string,
        so no test needed updating. Commit: pending (parent owns commit).

## Notes

- Cards view must remain a no-change path (same GET form, same querysets).
- f-block mapping: LANTANIDOS symbol La stays main-grid per data (all lan
  store group 3, period 6; Ce..Lu render in detached row below the table,
  classic IUPAC layout); same for Actínidos (Ac main, Th..Lr detached).
- Grid position is information: never remove cells from the grid, only
  dim/attenuate (didactic decision, obs #527).
- Suite baseline: 160 passed (local = 5f895a5 + gitignore commit).
- T7 observation (not fixed): the shared `<h1>` was shortened, but
  `{% block title %}` (browser tab title) still reads 'Tabla Periódica:
  Listado de Elementos'. Out of the delegated scope (the contract named the
  `<h1>` only); flagged for the operator to decide.
- Work-unit commits, Conventional Commits; push/PA only on explicit
  operator request.
- T4/T5 handoff from T3 (exact hooks the CSS/JS must target):
  container `#pt-tabla.pt-grid`; cells `a.pt-celda` with
  `pt-celda-<slug>` slugs `metales`, `no-metales`, `alcalinos`,
  `alcalinos-terreos`, `lantanidos`, `actinidos`,
  `metales-de-transicion`, `otros-metales`, `metaloides`,
  `otros-no-metales`, `halogenos`, `gases-nobles` (10 used by data today,
  12 chips rendered); `pt-sintetico` (Z>=104), `pt-fila-f` (detached rows),
  `#pt-leyenda .pt-chip[data-categoria]`, `#pt-buscar`, `#pt-peso-min`.
  Cells carry `data-categoria` (Spanish label), `data-simbolo` and
  `data-nombre` (both lowercased for search). The cell is the `<a>` itself
  (no inner wrapper div). Positions are inline `style` on each cell
  (grid-column/grid-row), so the CSS only defines the 18-column template and
  the look. T3 does not add the CSS/JS `<link>`/`<script>`: base.html has no
  `extra_css` block yet, so T4 must extend base.html or the template.
- T4/T5 handoff from T4 (state hooks the JS must drive):
  `.pt-dim` (attenuated) and `.pt-destacada` (highlight ring) on `a.pt-celda`;
  optional `.pt-chip[aria-pressed="true"]` for the active legend chip. Both
  states compose with the synthetic honesty filter through
  `--pt-gris`/`--pt-saturacion`, so no combination needs extra CSS.
  CSS/JS asset link added by T4 at the top of `{% block content %}` in
  elemento_lista.html (base.html was NOT modified); T5 must add its `<script>`
  the same way or use the existing `{% block extra_js %}` in base.html.
- Position deviation (T3): the task text said `columna = Z - 57` for the
  lanthanides, but that contradicts its own expected values (Ce col 4, Lu col
  17) and is off by 3. Implemented `columna = grupo + (Z - 57)` (= Z - 54),
  i.e. the detached row continues the sequence from La/Ac's stored column 3
  (classic IUPAC). Verified: Ce (9,4), Lu (9,17), Th (10,4), Lr (10,17),
  La (6,3), Ac (7,3), no cell collisions.
