# Feature: p1-password-recovery — gestor_quimico (BACKLOG)

Status: BACKLOG — planned, not started. Approved in planning session;
to be picked up in a later session.

Goal: password recovery for users who lose their credentials, plus optional
TOTP MFA as a second iteration.

Context established during exploration (do not re-explore from scratch):

- User model is Django's default (`django.contrib.auth.models.User`), so the
  `email` field exists and the built-in auth views work out of the box.
- No email backend is configured in `core/settings.py` yet.
- django-axes 8.3.1 already rate-limits login; its lockout/unlock flow must
  interoperate with the recovery flow (test: locked account -> admin unlock
  -> reset -> login).
- `python-decouple` is already in use for credentials via env vars.

## Tasks

- [ ] T1 Admin password change (no code): use the built-in admin "change
      password" form (does not require the old password). It rotates the
      password hash and invalidates active sessions. If axes locked the
      account, unlock it via the axes AccessAttempt admin entry.
- [x] T2 Email recovery flow (native Django): wire `PasswordResetView`,
      `PasswordResetDoneView`, `PasswordResetConfirmView`,
      `PasswordResetCompleteView` into `app_quimico/urls.py` with 4 templates
      styled like the existing auth templates. Add a "forgot password?" link
      on the login template.
- [x] T3 Email backend config: `EMAIL_BACKEND = console` for dev (see email in
      terminal); SMTP for the simulated-production profile via decouple env
      vars (Gmail app password ~500/day, or Brevo 300/day free tier). Never
      hardcode credentials; document in `.env.example`.
- [x] T4 Tests: reset request for existing and unknown email (same response,
      no user enumeration), token confirmation flow, invalid/expired token,
      password validators applied, axes interplay with the reset flow.
- [ ] T5 (follow-up iteration, separate feature): MFA with Google
      Authenticator via `django-otp` + `django-otp-totp` — enrolment with QR,
      second step in the login flow, admin integration. Requires the reset
      flow to be stable first. Intentionally excluded from this feature.

Rejected alternative (documented decision): secret question/answer recovery.
Weak pattern (answers cannot be rotated once leaked, easily guessable,
discouraged by OWASP) and more custom work than the native email flow.

## Decisions / notes

- Scope decision 2026-07-19 (planning session): user asked for an opinion;
  approved as backlog only, implementation deferred to the next session.
- Priority order agreed: T1 is free, T2-T4 are the core feature, T5 is a
  separate later iteration.
- Implementation 2026-09-19 (T2-T4): routes, templates, settings and tests
  written; `pytest app_quimico/tests/test_password_reset.py -q` 10 passed and
  full suite `pytest -q` 66 passed. Commit identity pending: the orchestrator
  owns the work-unit commit. T4's `password validators` and `axes interplay`
  items are covered by dedicated tests.
- Open item: `.env.example` documentation for the SMTP variables could not be
  written (tool-level safety guard blocks every `.env*` path); the orchestrator
  must record the documented block or authorize another route.
