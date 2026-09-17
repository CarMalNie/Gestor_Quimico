# Feature: P0 Hardening — gestor_quimico

Goal: bring the repository to a defensible professional baseline (security, ownership,
calculator correctness, compound form UX, README) without new features beyond the
agreed scope.

Decisions made with the operator (2026-09-17):
- Role matrix: Quimicos = product users (own compounds only). Colaboradores = master
  data curators (no compound access in the web app). Administradores = governance via
  Django admin only (no compound screens in the web app). Web compound views become
  strictly owner-scoped for everyone.
- Calculator: strict IUPAC input validation (reject `cU`, unknown chars,
  unbalanced brackets); hydrates (`CuSO4.5H2O`) explicitly rejected with a clear
  message; weights cached per process; service injectable weights for unit tests.
- Frontend stays on Bootstrap 5 (no Tailwind migration); cascade
  industria->aplicacion added with project JS + form-level cross validation.

## Tasks

- [x] T1 Settings hardening: env-driven settings (SECRET_KEY, DEBUG, DB credentials),
      `.env.example`, `python-decouple` added to requirements, `STATIC_ROOT` defined.
      NOTE: code complete + verified; `.env`/`.env.example` pending manual creation
      (safety policy blocks agent writes to .env*).
- [x] T2 Ownership/visibility: compound list/detail/update/delete strictly owner-scoped
      for every role in the web app; remove `is_global_manager` logic and group-based
      `UserPassesTestMixin` cross-user access; permission tests for the new matrix.
      (8 pytest tests green, manage.py check clean.)
- [x] T3 Calculator robustness: strict pre-validation (reject unknown characters,
      ambiguous `CU`/`cU`, unbalanced brackets), explicit rejection of hydrate syntax,
      weight cache, injectable weights; unit test suite for the parser.
- [x] T4 Compound form redesign: cascading industria->aplicacion selects (project JS),
      cross-validation in `clean()`, remove decorative `tipo_industria` behavior;
      tests for the validation.
- [x] T5 Professional README: no bootcamp vocabulary, no LaTeX artifacts, accurate
      stack, architecture summary, real setup, roadmap.
- [x] T6 Final verification: full test suite green, manage.py check, collectstatic
      sanity, no secrets tracked.
      (24 tests passed; check clean; collectstatic 129 files; git grep: no secrets in
      tracked files; .env/.env.example created by operator, .env.example now tracked.)

## Decisions / notes

- Ambiguity rule reverted (operator decision): two consecutive uppercase letters are
  no longer rejected. Strict IUPAC literalism: 'Cu' parses as copper (1 element),
  'CU' parses as C + U (2 elements, valid). 'cU'/'cu'/'uc' remain errors. This keeps
  'NH3' and 'HO' correct with the full 118-element table (no false positives from
  Nh/Ho existing as real elements).
- Tests: pytest + pytest-django (added to .venv; parser tests inject weights so they
  do not require the database).
- Verification DB: local MySQL (root) available; pytest-django creates a test DB.
- No commits during the session unless the user explicitly asks.
