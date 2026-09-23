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
- [ ] T3 Template: elemento_lista.html toggle buttons (cards/grid) + grid
      markup (CSS grid 18 cols x 7 rows + 2 detached f-block rows for
      Ce..Lu / Th..Lr; La/Ac stay at (P6,G3)/(P7,G3) per stored data) +
      legend chip row + client-side filter controls (search, peso
      threshold). Grid cell: Z, symbol, name; links to elemento_detalle.
      Cards branch byte-identical to current markup.
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
