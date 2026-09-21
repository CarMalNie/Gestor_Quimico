# Feature: p1-minors — detalles del frontend y menores del backlog

Backlog of small items agreed with the operator before the periodic-table
feature (backlog order obs #520 rev 2, reconciled 2026-09-21 against code
and live local DB).

## Reconciled status

- [x] Email site_name in body/subject — FIXED (2026-09-21, suite 137
      passed incl. new test_reset_email_uses_configured_site_name via pytest).
      Sender friendly name already worked (DEFAULT_FROM_EMAIL display name,
      operator-validated on PA). Subject/body rendered the domain because
      {{ site_name }} comes from get_current_site(request) and
      django.contrib.sites is not installed -> RequestSite = request host.
      Fix: settings.SITE_DISPLAY_NAME (env-configurable, default "Gestor
      Químico") + extra_email_context={'site_name': settings.SITE_DISPLAY_NAME}
      on PasswordResetView.as_view (app_quimico/urls.py). Template unchanged
      ("— Equipo de {{ site_name }}" -> "— Equipo de Gestor Químico"),
      operator-approved wording. .env.example example line to be added
      manually by operator (harness safety policy blocks agent edits there);
      production PA needs no .env change (default covers it). Evidence: 3-file
      diff, pytest 137 passed; commit pending operator request.
- [x] ~~MySQL timezone tables (local)~~ — RESOLVED: tz tables installed
      locally (mysql.time_zone / time_zone_name = 597 rows each, verified
      via Django shell 2026-09-21). Axes admin date-hierarchy pages work
      locally now. Supersedes obs #501 "no arreglar" decision. PA side
      verified by operator.
- [x] Navbar mobile polish — FIXED d38e03f (2026-09-21). templates/navbar.html
      fixed margins (me-3/me-2) replaced with responsive me-lg-*; right block
      gets align-items-lg-center + mb-2 mb-lg-0 in the collapsed menu. Check
      clean, suite green.
- [x] Calculator hydrate support (#484) — DONE c0b5a0b (2026-09-21).
      _SEPARADORES_HIDRATO now splits the formula into segments: anhydrous
      part + hydrate segments with optional leading positive-integer
      coefficient (default 1) multiplying the block. Counts and PM sum across
      segments; counting loop extracted to _contar_tokens (API unchanged).
      Strict validation kept (empty segment, coefficient 0, unbalanced group,
      unknown symbol). README roadmap item closed. Suite 146 passed at commit.
- [x] Force-MFA policy decision — DECIDED + IMPLEMENTED d5e3b61 (2026-09-21).
      Operator chose option B: MFA mandatory ONLY for Administradores.
      CustomLoginView.form_valid redirects an Administradores user without a
      confirmed TOTPDevice to mfa_setup with a warning message (stale
      unconfirmed devices do not count); everyone else keeps voluntary MFA
      and the second-factor flow is untouched. 6 new tests (test_force_mfa.py).
      Suite 152 passed at commit.
- [x] Seed "Administradores" group migration — DONE a1f91b9 (2026-09-21).
      Migration 0009 (idempotent get_or_create, reverse delete, depends on
      0008) + test_groups_seed.py asserting Quimicos/Colaboradores/
      Administradores exist post-migrate. makemigrations --check clean,
      migrate applied to dev DB, suite green.

## Evidence

- 2026-09-21 0985c0e fix(auth): nombre amigable en asunto y cuerpo del email
  de recuperacion (4 files, 26 insertions). Suite 137 passed (pytest -q).
  Implemented via gentle-ai-worker; .env.example line added by operator
  (harness policy blocks agent writes to .env*). Push/PA deploy pending
  explicit operator request.
- 2026-09-21 d38e03f fix(frontend): navbar responsiva en vista movil (1 file).
  Suite 137 passed, manage.py check clean.
- 2026-09-21 a1f91b9 feat(db): semilla del grupo Administradores (migration
  0009 + test_groups_seed). makemigrations --check clean, migrate applied,
  suite 138 passed.
- 2026-09-21 c0b5a0b feat(calculadora): soporte de hidratos (utils.py + tests
  + README roadmap). Suite 146 passed; focused module 28 passed.
- 2026-09-21 d5e3b61 feat(auth): MFA obligatorio para Administradores (gate
  en CustomLoginView + 6 tests). Suite 152 passed.

## Session close checkpoint (agreed with operator)

- Next session start: push (23387bc..d5e3b61), PA deploy (pull + migrate —
  0009 is new — + reload; no collectstatic needed), then operator validates
  in production: reset email shows "Gestor Químico" in subject/footer,
  navbar at phone width, CuSO4·5H2O calculation, admin login gate. ALL this
  validation happens BEFORE starting periodic-table work (itself before the
  2D diagram work). Operator checkpoint agreed: production email
  validation (subject/body show "Gestor Químico", link intact) scheduled
  BEFORE starting the 2D diagram work; risk is low (presentation-only change,
  template strings untouched, test covers the assertion).

## Notes

- Suite baseline: 137 passed (local = origin/main = 0985c0e).
- RDD review switch disabled clone-locally (pi review-relay bug; lineage
  review-1f4804d155c041e5 open, do not reset).
- Work-unit commits with Conventional Commits; push/PA deploy only on
  explicit operator request.
