# Feature: P1 Correctivos — gestor_quimico

Goal: close the remaining backend and frontend findings from the recruiter review
while keeping the Django monolith as the professional baseline. After this feature
the monolith meets the security bar required before CI/CD study (GitHub Actions)
and the future DRF phase.

Operator decisions (2026-09-17, resumed session):
- Finish the monolith professionalization first (backend + frontend).
- CI/CD learning phase (GitHub Actions) comes after, plus free deploy alternatives
  study; gate: security minimums met, ideal targets pursued.
- No commits or pushes unless the operator explicitly asks.

## Tasks

- [x] T1 Logout by POST: custom_logout_view now @require_POST (Django 5 already
      rejects GET on its LogoutView; the custom view was the gap). Template already
      used a POST form with CSRF.
- [x] T2 Messages without {e} leak: element create/update and compound
      create/update now show generic user messages + logger.exception() for detail.
      Parser ValueError messages (our own text) remain user-facing by design.
- [x] T3 Pagination: CompuestoListView paginate_by=12, template controls using
      Django 5.2 {% querystring %} (preserves filters). Test: 13 compounds ->
      page 1 has 12, page 2 has 1. 12 tests green in tests.py.
- [x] T4 Data migration 0003_setup_groups: creates Quimicos (no model perms) and
      Colaboradores (add/change industria, aplicacion, elementoquimico,
      detalleelemento) groups. Permissions created explicitly in the migration
      (auth post_migrate has not run yet on fresh DBs); depends on
      contenttypes 0002 (legacy ContentType.name column). Test reuses the
      migrated group via get_or_create.
- [x] T5 Unify constraints: three unique_together replaced by named
      UniqueConstraint (0004). Suite 32 green.
- [x] T6 fecha_registro_compuesto: auto_now_add=True (0005); unused timezone
      import removed from models.py.
- [x] T7 Email uniqueness: RegistroForm.email required + clean_email
      case-insensitive duplicate check; 2 new tests.
- [x] T8 Service layer: app_quimico/services.py with calcular_pm (parse +
      quantize Decimal 0.0001) and registrar_elementos_compuesto (delete +
      bulk_create, requires saved compound); create/update views refactored to
      use it (~40 duplicated lines removed); tests/test_services.py with 4 tests.
- [x] T9 Frontend sweep: BS4 classes replaced (text-right->text-md-end,
      font-weight-bold->fw-bold, ml-2->ms-2); messages block extracted to
      templates/messages.html (single include in base.html); Bootstrap 5.3.3
      self-hosted in static/vendor/bootstrap (css + bundle js); Font Awesome
      stays on cdnjs 5.15.4 with SRI fetched from the cdnjs API (never
      hand-typed). No fabricated SRI hashes.
- [x] T10 Final verification: 38 tests green, check clean, makemigrations
      --check clean, collectstatic 131 files (+2 vendor), no secrets tracked.

## Decisions / notes

- Logout: POST-only custom view (defence in depth even though the template was
  already correct).
- Migration 0003 creates auth permissions inside itself via
  create_contenttypes + create_permissions because post_migrate has not run on
  fresh databases; explicit dependency on contenttypes 0002 avoids the legacy
  ContentType.name NOT NULL column (MySQL error 1364).
- Weight-cache invalidation fixture moved to app_quimico/conftest.py (autouse for
  all app tests) after a cache leak across test files was diagnosed.
- Bootstrap self-hosted (no CDN): same-origin files need no SRI; SRI kept for
  the one remaining external dependency (Font Awesome). Version-pinned 5.3.3.
- Operator must run `python manage.py migrate` on the local dev DB to apply
  0003-0005 (adds groups + constraint changes; no destructive ops).

## Evidence

- Commits: 8ca70ed fix(review) (hallazgos R3), 338d513 feat(services),
  d4f76c8 feat(backend) (paginación adoptada en views), 7295217 feat(models),
  c465c30 feat(groups), 773e6e1 feat(frontend), 963a43e chore(tasks).
