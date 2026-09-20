# Feature: p1-mfa-totp — gestor_quimico

Status: IN PROGRESS — approved 2026-09-20 (operator order: credentials cycle;
password-change shipped first, MFA next).

Goal: optional TOTP MFA (Google Authenticator compatible) via `django-otp` +
`django-otp-totp`: enrolment with QR, second step in the login flow, admin
integration. Follow-up iteration of p1-password-recovery (T5 as originally
scoped).

Context established during exploration (do not re-explore from scratch):

- Login is `CustomLoginView(LoginView)` in `app_quimico/views.py` (adds a
  success message). The MFA second step must interoperate, not replace it.
- `AUTHENTICATION_BACKENDS`: `axes.backends.AxesStandaloneBackend` first, then
  `django.contrib.auth.backends.ModelBackend`. django-otp's backend must slot
  after axes. `OTPMiddleware` goes after
  `django.contrib.auth.middleware.AuthenticationMiddleware`.
- User model is Django default User; `django-axes` blocks `client.login()` in
  tests — login via HTTP POST to the login route (pattern in
  `test_password_reset.py` / `test_password_change.py`).
- crispy-forms + bootstrap5 is the form styling convention.
- Django 5.2.8; requirements.txt pins exact versions.
- QR generation: prefer `qrcode` with its SVG factory (no new Pillow
  dependency) rendering the `otpauth://` provisioning URI server-side.

## Tasks

- [x] T1 Dependencies + settings: pin `django-otp`, `django-otp-totp`, `qrcode`
      in requirements.txt; add `django_otp` and
      `django_otp.plugins.otp_totp` to INSTALLED_APPS; `OTPMiddleware` after
      auth middleware; OTP-aware backend after axes; `manage.py check` clean.
      DEPLOYMENT NOTE: PythonAnywhere runs this project online — after these
      commits are pulled there, the web app's virtualenv MUST run
      `pip install --upgrade pip && pip install -r requirements.txt`
      (or add the three packages individually), then the web app needs a
      reload. New migrations (T2/T3) require `python manage.py migrate` in the
      PA console too. Do this only when the operator decides to deploy.
- [x] T2 Enrolment: protected route `/accounts/mfa/setup/` (`mfa_setup`,
      login required): create/reuse an unconfirmed TOTP device, render QR
      (provisioning URI) + confirm code form; on valid code, confirm the
      device (activation). Template styled like auth templates.
- [x] T3 Login second step: after successful password login, if the user has
      a confirmed TOTP device, redirect to `/accounts/mfa/verify/`
      (`mfa_verify`) asking for the 6-digit code; on valid token mark the
      session verified (django_otp.login) and proceed (welcome message
      preserved); wrong code retries with form error; anonymous access
      redirects to login. Users WITHOUT a device log in exactly as today.
- [x] T4 Admin integration: `django_otp` + `otp_totp` admin wired (device
      admin under User, per django-otp docs) so staff can inspect/remove
      devices.
- [x] T5 Tests (`app_quimico/tests/test_mfa_totp.py`): enrolment requires
      login; QR + confirm flow activates the device; wrong confirm code does
      not activate; login with confirmed device requires the token (wrong
      code rejected, session not verified); correct token completes login;
      user without device logs in as before; axes interplay: too many failed
      token attempts do not bypass axes lockout rules; logout works with
      OTPMiddleware installed.
- [x] T6 Close: full suite green, work-unit commit (Conventional Commit),
      evidence recorded in this doc.

Rejected alternative: custom TOTP implementation (RFC 6238 by hand). Risky,
duplicates a well-tested library, and loses the django-otp admin/plugin
ecosystem.

Rejected alternative: SMS/email OTP. Requires an external SMS provider or
burns the free email quota; TOTP is the agreed scope (Google Authenticator).

## Evidence

- T1: `requirements.txt` pins `django-otp==1.7.3` + `qrcode==8.2`;
  `INSTALLED_APPS` adds `django_otp` + `django_otp.plugins.otp_totp`;
  `OTPMiddleware` placed right after `AuthenticationMiddleware`.
  `manage.py makemigrations --check --dry-run` -> "No changes detected"
  (the plugin ships its own migrations).
- T2/T4: `.venv/Scripts/python.exe manage.py check` -> "System check
  identified no issues (0 silenced)."; TOTPDevice is registered by
  `TOTPDeviceAdmin` and `/admin/otp_totp/totpdevice/` resolves.
- T3: orchestrator approved option A and extended the allowed edit surfaces
  with `app_quimico/views.py`; `CustomLoginView.form_valid` now redirects a
  user with a confirmed `TOTPDevice` to `mfa_verify` before the welcome
  message, and keeps today's behaviour otherwise.
- T5: `pytest app_quimico/tests/test_mfa_totp.py -q` -> 21 passed.
- Full suite: `pytest -q` -> 96 passed (baseline before the feature: 75).
- 2026-09-20 c0277c7 feat(auth): MFA TOTP opcional con django-otp (T1-T5
  completos: deps django-otp 1.7.3 + qrcode 8.2, settings con OTPMiddleware,
  enrolamiento QR en /accounts/mfa/setup/, segundo paso /accounts/mfa/verify/
  con ?next= preservado, 21 tests MFA; suite 96 passed). Verificación
  independiente gentle-ai-verify: PASS en 5 checks (scope, seguridad
  mfa_views, form_valid, comandos, sin archivos fuera de lista).
- Deployment (operator-owned): PythonAnywhere necesita `pip install -r
  requirements.txt` (django-otp, qrcode), `python manage.py migrate`
  (tabla otp_totp_totpdevice) y recarga de la web app. Operador se encarga
  de estos pasos y de la activación SMTP del email de reset en ese momento.

## Decisions / notes

- `next` forwarding through the second step (T3/T5): `CustomLoginView.form_valid`
  preserves the original `?next=` when it differs from `reverse(LOGIN_REDIRECT_URL)`
  and appends it as `?next=<quote(next_url)>` to the `mfa_verify` redirect;
  `mfa_verify` revalidates it with `url_has_allowed_host_and_scheme` before
  honouring it and otherwise falls back to `LOGIN_REDIRECT_URL`. Covered by
  `test_login_with_confirmed_device_forwards_next_to_mfa_verify` (quoting round
  trip), `test_verify_with_valid_token_honours_next` (destination wins over
  `perfil_personal`) and the `test_login_without_device_honours_next` regression
  guard.

- RESOLVED (T3/T5): the second-step redirect required an override inside
  `CustomLoginView` in `app_quimico/views.py`, outside the original allowed
  edit surfaces, so the worker stopped and reported it. The orchestrator
  approved option A and extended the surfaces; the override was implemented
  there and the temporary `xfail` marker was removed from
  `test_login_with_confirmed_device_redirects_to_mfa_verify`, which now
  asserts the real redirect and that the welcome message is withheld until
  the token is verified.
- Deviations found during T1 (documented, no scope expansion):
  - `django-otp-totp` does not exist on PyPI (`pip index versions` -> "No
    matching distribution found"). The TOTP plugin ships inside `django-otp`
    as `django_otp.plugins.otp_totp`; pinning a phantom package is impossible.
    Only `django-otp==1.7.3` + `qrcode==8.2` were pinned.
  - `django_otp.backends.ModelBackend` does not exist in django-otp 1.7.3
    (the installed wheel has no `backends.py`). django-otp needs no
    authentication backend: the second factor is enforced by `OTPMiddleware`
    + `django_otp.login()`. `AUTHENTICATION_BACKENDS` is therefore unchanged
    (`AxesStandaloneBackend` first, then `ModelBackend`).
  - `makemigrations` created no files: the plugin already ships 0001-0003.
    The PA deployment still needs `manage.py migrate` to create the
    `otp_totp_totpdevice` table.
- BLOCKED (T3/T5): the second-step redirect needed an override inside
  `CustomLoginView` in `app_quimico/views.py`, which was outside the allowed
  edit surfaces. Per the scope guard, no write was made there; the exact
  needed edit was reported to the orchestrator (option A). Resolved after
  approval, see the RESOLVED note above.
- T3 wording "redirect home" vs. today's behavior: `LOGIN_REDIRECT_URL` is
  `perfil_personal` and the existing suite asserts it
  (`test_password_change.py::test_new_password_authenticates_while_old_one_does_not`).
  To "behave exactly as today", `mfa_verify` redirects to
  `resolve_url(LOGIN_REDIRECT_URL)` (with a validated `?next=` override),
  not to the `home` route.
- Order decision 2026-09-20: operator picked MFA right after the password
  change feature; recovery/reset cycle already closed (CI green).
- Review gate note: RDD is clone-local OFF in this repo (temporary, pi relay
  bug upstream); CI in GitHub Actions is the active safety net.
- Scope guard: enrolment is optional per user; nobody is forced to enrol.
  Force-all-users policy is a later product decision, not in this feature.
- Deployment (operator reminder 2026-09-20): the project is LIVE on
  PythonAnywhere. Every new pinned dependency (requirements.txt) and every
  migration needs the PA virtualenv updated (`pip install -r
  requirements.txt`) + `manage.py migrate` + web app reload before users
  see the feature. Same applies retroactively: password-recovery and
  password-change had no new deps or migrations, but MFA does.
