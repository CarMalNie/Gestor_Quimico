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
- [ ] T4 CSS: static/css/periodic_table.css — category color map for all 12
      CATEGORIA_CHOICES via CSS custom properties, [data-bs-theme="light"|"dark"]
      variants, honesty styling class (dashed/muted) for Z>=104,
      .pt-dim/.pt-highlight state classes, responsive fallback (scroll or
      reduced cells on small screens; readable >= lg).
- [ ] T5 JS: static/js/periodic_table.js — vanilla-only: legend chip
      hover/click handlers, search input highlight (symbol/name), peso
      threshold dimming; AND-combined classes; no server round-trips.
- [ ] T6 Full pytest suite green + evidence + work-unit commits per task;
      push + PA deploy (pull + reload + collectstatic if CSS/JS added)
      on explicit operator request; production validation with operator.

## Notes

- Cards view must remain a no-change path (same GET form, same querysets).
- f-block mapping: LANTANIDOS symbol La stays main-grid per data (all lan
  store group 3, period 6; Ce..Lu render in detached row below the table,
  classic IUPAC layout); same for Actínidos (Ac main, Th..Lr detached).
- Grid position is information: never remove cells from the grid, only
  dim/attenuate (didactic decision, obs #527).
- Suite baseline: 160 passed (local = 5f895a5 + gitignore commit).
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
- Position deviation (T3): the task text said `columna = Z - 57` for the
  lanthanides, but that contradicts its own expected values (Ce col 4, Lu col
  17) and is off by 3. Implemented `columna = grupo + (Z - 57)` (= Z - 54),
  i.e. the detached row continues the sequence from La/Ac's stored column 3
  (classic IUPAC). Verified: Ce (9,4), Lu (9,17), Th (10,4), Lr (10,17),
  La (6,3), Ac (7,3), no cell collisions.
