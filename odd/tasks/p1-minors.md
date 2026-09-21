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
- [ ] Navbar mobile polish — PENDING. templates/navbar.html is
      `navbar-expand-lg fixed-top` with fixed `me-3`/`me-2` spacing; items
      crowd at phone width. Fix: responsive spacing (gap utilities),
      collapse behavior, theme-toggle/username/logout alignment in the
      collapsed menu.
- [ ] Calculator hydrate support (#484) — PENDING. utils.py still
      deliberately rejects hydrate separators ('.', '·', '⋅', '∙',
      _SEPARADORES_HIDRATO) with a friendly Spanish message. Plan (obs
      #484): tokenize hydrate separator (· + optional coefficient, e.g.
      ·5H2O multiplies the H2O block), sum into element counts and PM,
      replace rejection, add tests (happy path, explicit coefficient,
      implicit coefficient 1, balance). Bracket mixing () [] {} already
      supported and test-covered.
- [ ] Force-MFA policy decision — PENDING (product decision, no code):
      decide whether MFA becomes mandatory (login gate for all users) or
      stays voluntary. Operator decision needed.
- [ ] Seed "Administradores" group migration — PENDING. 0003_setup_groups
      only creates Quimicos/Colaboradores; Administradores was created
      manually in the PA admin (badge fix, obs "Badge (Administradores)
      arreglado en PA"). Seed it in the migration chain so fresh
      environments get all three groups.

## Evidence

- 2026-09-21 0985c0e fix(auth): nombre amigable en asunto y cuerpo del email
  de recuperacion (4 files, 26 insertions). Suite 137 passed (pytest -q).
  Implemented via gentle-ai-worker; .env.example line added by operator
  (harness policy blocks agent writes to .env*). Push/PA deploy pending
  explicit operator request. Operator checkpoint agreed: production email
  validation (subject/body show "Gestor Químico", link intact) scheduled
  BEFORE starting the 2D diagram work; risk is low (presentation-only change,
  template strings untouched, test covers the assertion).

## Notes

- Suite baseline: 137 passed (local = origin/main = 0985c0e).
- RDD review switch disabled clone-locally (pi review-relay bug; lineage
  review-1f4804d155c041e5 open, do not reset).
- Work-unit commits with Conventional Commits; push/PA deploy only on
  explicit operator request.
