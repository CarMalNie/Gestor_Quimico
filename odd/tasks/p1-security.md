# Feature: p1-security — gestor_quimico

Goal: reach the ideal security bar for a Django monolith (headers, HSTS gating,
login rate limiting) after the P0 minimums, before CI and any deploy.

Operator decisions (2026-09-17):
- Security review first, CI later; dark/light theme toggle noted as a small
  follow-up frontend feature (Bootstrap 5.3 native, after CI).

## Tasks

- [x] T1 Settings hardening (ideal tier): ALLOWED_HOSTS from env (comma list),
      security headers always on (nosniff, Referrer-Policy same-origin,
      X-Frame-Options DENY), HTTPS-gated flags via env (SECURE_HSTS_SECONDS,
      SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE; default
      off for local dev), .env.example documented.
- [x] T2 Login rate limiting: django-axes 8.3.1 (requirements pinned),
      AxesStandaloneBackend first in AUTHENTICATION_BACKENDS, AxesMiddleware,
      AXES_ENABLED env flag, limit 5 attempts with 1h cool-off.
- [x] T3 Tests: test_security.py — headers present on responses, lockout after
      5 failures (429) blocking even the correct password, reset returns to
      successful login. Autouse fixture clearing AccessAttempt for isolation.
- [x] T4 Final verification: 41 tests green, check clean, makemigrations
      --check clean; README security section expanded with the new measures.

## Decisions / notes

- HTTPS-dependent flags default to False because the local dev server is HTTP;
  they are intended to be enabled via env when deploying (PythonAnywhere
  provides HTTPS automatically).
- axes default lockout response status is 429 (Too Many Requests) in v8.
- Operator has a PythonAnywhere account; deploy plan: CI first, then
  PythonAnywhere as CD exercise (its free tier includes MySQL + HTTPS).

## Evidence

- (commits recorded per task once operator authorizes)
