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
- [ ] T4 Staged form UX: compuesto_form.html — Bootstrap collapse entry
      button "¿Agregar estructura 2D?" wrapping the smiles field; opt-out
      button "No — mejor sin estructura" collapses and clears the input;
      didactic help accordion "¿Qué es esto?" with ethanol CCO vs dimethyl
      ether COC copy; existing two-card layout untouched otherwise; cards
      view of create page without expansion = identical DOM. JS minimal
      (static/js or inline) for opt-out clear; cache-busting convention.
- [ ] T5 Render: vendor smiles-drawer.min.js under static/vendor/
      smilesdrawer/ (downloaded by parent, not pip); card list render in
      compuesto_lista.html inside `{% if compuesto.smiles %}` (cards
      byte-identical without SMILES); detail render in compuesto_detalle;
      fixed light canvas independent of data-bs-theme (documented choice);
      CSS scoped additions; `?v=1` cache-bust on new asset.
- [ ] T6 Full pytest suite green + manage.py check + makemigrations --check
      clean; PA deploy notes (pip install pysmiles + collectstatic +
      migrate); work-unit commits.

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
