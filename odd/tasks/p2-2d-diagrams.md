# Feature: p2-2d-diagrams — Estructura 2D de compuestos (Entrega 1, núcleo SMILES)

Sealed design: Engram obs #516 (v4). Entrega 1 is self-contained (no external
APIs): optional `smiles` on CompuestoQuimico, staged create/edit form UX,
backend SMILES validation via pysmiles, self-hosted SmilesDrawer rendering.
Entrega 2 (PubChem lookup) is a separate delivery — NOT in this feature.

## Scope (Entrega 1)

- Optional `smiles` field on CompuestoQuimico (empty = today's behavior
  exactly: no diagram, card unchanged).
- Create/edit form: collapsed entry button "¿Agregar estructura 2D?" —
  nothing chemical visible until clicked; expands to direct SMILES input
  (backend-validated with pysmiles) + explicit opt-out "No — mejor sin
  estructura" (collapses and clears the field).
- Didactic collapsible "¿Qué es esto?" help: SMILES notation, ethanol CCO
  vs dimethyl ether COC, why optional.
- Render: self-hosted SmilesDrawer (static/vendor), client-side, on card
  (list) and detail. Diagram shown ONLY when SMILES present.
- Bootstrap 5.3.3 collapse (data-bs-toggle) — zero/minimal custom JS.

Rejected/sealed: RDKit (PA free tier disk), bubble SVG diagrams (chemical
honesty), always-visible structure section, PubChem (Entrega 2).

## Tasks

- [x] T1 Feature doc + Engram mirror + todo projection (this doc)
- [x] T2 Backend: `smiles` field on CompuestoQuimico (TextField, null=True,
      blank=True, no unique; verbose_name 'Estructura SMILES'), migration
      0010, no other model change. Tests for the field presence/migration.
      + Evidence: app_quimico/models.py L147-152 (field between
        fecha_registro_compuesto and Meta; Meta/__str__ unchanged).
      + Evidence: app_quimico/migrations/0010_compuestoquimico_smiles.py
        (deps 0009, single AddField, options match model).
      + Evidence: app_quimico/tests/test_compuesto_smiles.py — 7 tests
        (field definition, migration applied via MigrationRecorder +
        introspection, create without/with SMILES, get_or_create FK
        pattern, __str__ regression).
      + Checks (.venv/Scripts/python.exe): pytest -q baseline 187 passed ->
        194 passed after (no regressions); manage.py check clean;
        makemigrations --check --dry-run: no changes detected.
      + Commit: parent owns (work-unit commit below).
- [x] T3 Validation + form + views: pysmiles added to requirements.txt;
      `clean_smiles` on CompuestoQuimicoForm (empty is valid = opt-out;
      invalid SMILES -> form error, Spanish message); form Meta.fields adds
      `smiles`; CompuestoCreateView.post and CompuestoUpdateView.post must
      persist `smiles` (create: from cleaned_data; update: form.save path
      or instance wiring — verify actual manual post() flow and wire it
      through the same is_valid/saved path as formula). Tests: valid SMILES
      accepted (CCO), invalid rejected with error, empty accepted (no
      diagram), persisted on create and update.
      + Evidence: requirements.txt L8-9 (networkx==3.7, pysmiles==2.1.0,
        installed in .venv).
      + Evidence: app_quimico/forms.py L14 import, L18-20 SMILES_ERROR,
        L117 Meta.fields + smiles, L125-128 widget, L141 crispy fieldset,
        L145-172 clean_smiles (empty->None opt-out, outer strip, internal
        whitespace rejected, read_smiles try/except).
      + Evidence: views.py NOT edited — persistence rides the existing
        path: create save(commit=False) L462 -> save() L476; update L635 ->
        L649/L655 (construct_instance writes smiles before save). Tests
        assert create persists CCO, opt-out stores None, update sets/clears.
      + Evidence: test_compuesto_smiles.py +10 tests (17 in file: form
        field wiring, valid/strip/empty, invalid, internal whitespace,
        create persists/opt-out, update new/clear).
      + Checks: pytest -q full suite 194 -> 204 passed; manage.py check
        clean; makemigrations --check clean. RED first: 9 failed, 8 passed
        pre-implementation; GREEN 17/17 focused.
      + Follow-up flagged: pysmiles lenient — 'XYZ' yields 0-node graph
        without raising; 0-atom graphs must be rejected (hardening folded
        into T4 scope).
      + Commit: parent owns (work-unit commit below).
- [x] T4 Staged form UX: compuesto_form.html — Bootstrap collapse entry
      button "¿Agregar estructura 2D?" wrapping the smiles field; opt-out
      button "No — mejor sin estructura" collapses and clears the input;
      didactic help accordion "¿Qué es esto?" with ethanol CCO vs dimethyl
      ether COC copy; existing two-card layout untouched otherwise.
      + Evidence: compuesto_form.html L45-91 (entry button L46-51,
        #estructura2d L53, label+field L55-59, hint L61-63, error block
        L65-69, help accordion #smiles-ayuda L70-87, opt-out #smiles-opt-out
        L89-91) + inline opt-out JS in extra_js L146-163 (bootstrap.Collapse
        with classList fallback); smiles errors auto-open the collapse
        server-side (show class + aria-expanded synced).
      + Hardening folded (T3 flag): forms.py L169-176 — clean_smiles now
        rejects 0-atom graphs ('XYZ' parsed to 0-node networkx graph by
        pysmiles without raising); empty opt-out path unchanged.
      + Evidence: test_compuesto_smiles.py +8 tests (hardening L209-231,
        template L411-490: create+edit shared render, entry button,
        collapse with input, help, opt-out wiring, error autopen).
      + Checks: pytest -q full suite 204 -> 212 passed; focused file 25
        passed; manage.py check clean. RED: 7 failed, 18 passed pre-fix.
      + Known limit: opt-out JS not covered by pytest (no JS runner; tiny
        guarded vanilla script).
      + Commit: parent owns (work-unit commit below).
- [x] T5 Render: vendor smiles-drawer.min.js under static/vendor/
      smilesdrawer/ (downloaded by parent, not pip); card list render in
      compuesto_lista.html inside `{% if compuesto.smiles %}` (cards
      byte-identical without SMILES); detail render in compuesto_detalle;
      fixed light canvas independent of data-bs-theme (documented choice);
      CSS scoped additions; `?v=1` cache-bust on new asset.
      + Evidence: static/vendor/smilesdrawer/smiles-drawer.min.js (v2.0.3
        unpkg, 183KB, node --check OK; bundle exposes window.SmilesDrawer
        with SvgDrawer/parse).
      + Evidence: compuesto_lista.html L67-74 diagram block after formula
        badge ({% if %} glued to existing tags: zero whitespace shift when
        no SMILES) + extra_js block L182-188 (vendor + smiles_render.js?v=1
        only there).
      + Evidence: compuesto_detalle.html — new tab "Estructura 2D" in the
        existing nav-tabs row (L68-76) + pane L149-157; extra_js guarded
        by {% if compuesto.smiles %} (L166-173).
      + Evidence: static/js/smiles_render.js — IIFE, no-op without
        [data-smiles] (L72) or missing global (L77-83); per element:
        SmilesDrawer.parse -> new SvgDrawer({width,height}) -> draw(tree,
        svg, 'light'); fixed light bg documented in header.
      + Evidence: static/css/styles.css L137-166 sección estructura-2d
        (max-width 240px, bg #ffffff fijo, caption, svg responsive);
        templates/base.html L29 styles.css ?v=2 -> ?v=3 (bump por edición).
      + Evidence: test_compuesto_smiles.py L494-648 — 8 tests (lista/detalle
        con y sin SMILES, asset vendoreado, contrato estático del JS,
        scripts no globales en base, bump ?v=3).
      + Checks: pytest -q full suite 212 -> 220 passed; focused file 33
        passed; manage.py check + makemigrations --check clean;
        node --check smiles_render.js OK; byte-identity verified via SHA
        (Django render HEAD vs worktree, card loop and detail content block
        without SMILES identical).
      + Commit: parent owns (work-unit commit below).
- [x] T6 Full pytest suite green + manage.py check + makemigrations --check
      clean; PA deploy notes (pip install pysmiles + collectstatic +
      migrate); work-unit commits.
      + Checks: full pytest -q -> 220 passed (observed by writer and by
        independent verify, 296s); manage.py check clean;
        makemigrations --check --dry-run: no changes detected.
      + Independent verify (gentle-ai-verify): 15/15 PASS — suite, checks,
        structural readback of all T2-T5 surfaces (models L147, migration
        0010, forms clean_smiles guards L169-175, staged UX template,
        guarded list/detail blocks, smiles_render.js node-check, vendor
        bundle 183KB, base.html ?v=3), tree clean, 5 work-unit commits
        present, requirements pinned.
      + Work-unit commits: 8299943 (T2), d6976ad (T3), d92ac30 (T4),
        6af6fc0 (docs T4), 08ab546 (T5).
      + PA deploy notes (operator-owned steps, at deploy time):
        1) git pull; 2) pip install -r requirements.txt inside the venv
        (pysmiles + networkx NEW deps); 3) python manage.py migrate
        (0010 adds smiles column); 4) collectstatic --noinput (REQUIRED:
        new smiles_render.js + vendor smiles-drawer + styles.css edit);
        5) reload web app.
      + Local dev env: .venv already has pysmiles 2.1.0/networkx 3.7
        installed by T3.

- [x] T7 Bond-type didactic caption (agreed B+ design, operator request:
      NaCl case showed the card cannot say "ionic" alone for mixed
      compounds like NaClO): helper classifies the parsed SMILES graph —
      multiple fragments or nonzero net charge -> "Estructura iónica" with
      the separated species listed (Na⁺ · Cl⁻, Na⁺ · ClO⁻ — the internal
      covalent bonds are visible in the drawing itself, never re-stated);
      single connected neutral fragment -> "Enlace covalente"; orientative
      nature confessed in the "¿Qué es esto?" help (zwitterion caveat).
      Caption REPLACED-AGREED: heading kept, classified caption added
      below (parent task wording wins over doc's 'replaces' phrasing).
      + Evidence: (worker T7 fills here).
      + Evidence: app_quimico/models.py — clasificar_enlace_smiles() +
        _etiqueta_especie/_superindice_carga (Hill order, implicit-H
        aware, dedup, defensive None); KEY: pysmiles read_smiles joins
        '.' fragments with zero-order bonds by default (networkx sees 1
        component) -> zero_order_bonds=False required for the fragment
        rule. compuesto_lista.html/compuesto_detalle.html caption line
        below the heading (kept heading + added caption per parent task;
        doc text reconciled by parent). compuesto_form.html orientative
        paragraph in #smiles-ayuda. Tests +25 (classification units,
        negatives never raise, dedupe, implicit-H labels, captions,
        no-caption regressions, help copy).
      + Checks: pytest -q 222 -> 247 passed; focused file 60 passed;
        check + makemigrations clean. RED: 22 failed, 3 passed pre-fix.
      + Commit: parent owns (work-unit commit below).
- [x] T8 Final suite + checks after T7; PA deploy notes unchanged.
- [x] T9 Heteroatom-H expansion (agreed option C, didactic): server-side
      helper expands implicit hydrogens attached ONLY to O/N/S into explicit
      [H] atoms (pysmiles graph -> add H vertices per default valence minus
      bond order minus |charge| -> write_smiles), so water 'O' renders
      H-O-H and glucose OH renders H-O-C while C-bonded H stays condensed.
      data-smiles in both templates uses the expanded SMILES (stored SMILES
      and T7 caption logic unchanged); defensive fallback to original
      SMILES on any failure. Revert the T-experiment explicitHydrogens
      toggle in smiles_render.js (drawer default already draws written
      [H] atoms). Tests: expansion units (water 2 H, glucose 5 OH — ring
      ether O gets 0 H, hypochlorite O- gets 0 H, carbon H untouched),
      template wiring, failure fallback.
      + Blocked-then-unblocked: pysmiles write_smiles strips [H] via
        remove_explicit_hydrogens -> parent chose strategy A (H nodes
        tagged isotope='' skip the strip; post-write '[H]' guard falls
        back to original; pinned-dep contract test fails loudly on upgrade).
      + Evidence: static/js/smiles_render.js reverted byte-identical to
        committed; templates ?v=1 restored.
      + Evidence: app_quimico/utils.py L48-107 (_ELEMENTOS_H_EXPLICITOS,
        expandir_heteroatomos, isotope='' marker L96, '[H]' guard L107,
        4 fallback paths); app_quimico/models.py L267-281 smiles_para_render
        (local import anti-circularity, '' when no smiles, original on
        unparsable); compuesto_lista.html L68 + compuesto_detalle.html L151
        data-smiles="{{ compuesto.smiles_para_render }}"; T7 caption and
        {% if compuesto.smiles %} untouched.
      + Evidence: test_compuesto_smiles.py +19 tests (L862+): water 2 H,
        glucose 5 H + 0 H on carbons, hypochlorite unchanged, ethanol
        [H]OCC, benzene 0, nitric-acid N 0 H, negatives never raise,
        template wiring, loud upgrade-contract test; 4 CCO assertions
        updated to expanded form.
      + Checks: pytest -q 247 -> 266 passed; focused file 79 passed;
        check + makemigrations clean; node --check OK. RED: ImportError
        pre-implementation; 3 structural failures mid-cycle corrected
        (isolating written [H] via _h_sobre_heteroatomos).
      + Commit: parent owns (work-unit commit below).
- [x] T10 Final suite + checks after T9; PA deploy notes unchanged.
      + Independent verify (gentle-ai-verify) 5/5 PASS: pytest -q 266
        passed (291s); check + makemigrations clean; structural readback
        (no explicitHydrogens experiment left, node --check OK, both
        templates data-smiles=smiles_para_render + ?v=1 + guards intact,
        utils helper with isotope='' + '[H]' guard + 4 fallbacks, models
        method, form disclaimer, loud pin-contract test present); tree
        fully clean; commits 4dd21c0 + 0061bc9 verified.
      + Functional spot-check: 'O' -> data-smiles '[H]O[H]' + caption
        'Enlace covalente'; '[Na+].[Cl-]' -> caption 'Estructura iónica'
        with Na⁺ · Cl⁻ labels. PA deploy notes unchanged (T6).

## Notes

- Create/Update views are TemplateView with manual two-form post() handling
  (NOT generic CreateView/UpdateView) — `smiles` persistence must be wired
  through their actual save path; do not assume ModelForm.save() is called.
- Card markup is inline in compuesto_lista.html loop (no partial).
- Test DB (MySQL) seeds Industria/Aplicacion via migrations 0007/0008 —
  tests must use get_or_create, never create().
- axes: tests log in via POST to reverse("login") (client.login rejected).
- base.html has NO extra_css block; page CSS goes inline in content block
  (project convention) — SmilesDrawer CSS kept minimal or in styles.css.
- compuesto_cascade.js loads without cache-busting (pre-existing; out of
  scope unless touched).
- pysmiles dependency: pure Python (networkx); PA pip install required at
  deploy time.
