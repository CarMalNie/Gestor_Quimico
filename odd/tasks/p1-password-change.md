# Feature: p1-password-change — gestor_quimico

Status: IN PROGRESS — approved 2026-09-20 (operator pick: credentials cycle
before MFA).

Goal: self-service password change for authenticated users, complementing the
already-shipped email reset (p1-password-recovery) and the native admin change
form.

Context established during exploration (do not re-explore from scratch):

- No `PasswordChangeView` exists yet (grep over `app_quimico/` returned
  nothing). Only reset-by-email (`/accounts/`, shipped in aeff9fa) and admin.
- `perfil_personal.html` is the natural place for the entry link.
- Auth templates live in `app_quimico/templates/app_quimico/autenticacion/`;
  follow the styling of `password_reset_form.html`.
- Django's native `PasswordChangeView` + `PasswordChangeDoneView` handle the
  old-password check, validators, and `update_session_auth_hash` (session
  survives the change). `login_required` applies (LoginRequiredMixin built in
  via `password_change` views' `@login_required`-equivalent dispatch).
- Tests follow the `test_password_reset.py` pattern (native reset routes).

## Tasks

- [x] T1 Routing: wire `PasswordChangeView` + `PasswordChangeDoneView` into
      `app_quimico/urls.py` under `/accounts/password-change/` (names
      `password_change`, `password_change_done`), authentication enforced.
- [x] T2 Templates: `password_change_form.html` + `password_change_done.html`
      styled like the existing auth templates; add a "change password" link on
      the profile page (`perfil_personal.html`).
      Path note 2026-09-20: the allowed edit surface listed
      `app_quimico/templates/app_quimico/perfil_personal.html`, which does not
      exist. `find` showed the only `perfil_personal.html` lives at
      `app_quimico/templates/app_quimico/autenticacion/perfil_personal.html`
      (matching `template_name='app_quimico/autenticacion/perfil_personal.html'`
      in urls.py). The operator approved the corrected path and the link was
      added there.
- [x] T3 Tests (`app_quimico/tests/test_password_change.py`): unauthenticated
      redirect to login; wrong old password rejected; weak new password
      rejected by validators; successful change logs the expected redirect and
      the session survives (`update_session_auth_hash`); done page reachable.
- [ ] T4 Close: full suite green, work-unit commit (Conventional Commit),
      evidence recorded in this doc.

Rejected alternative: custom change-password form logic. Native views already
cover validation, old-password check, and session-hash rotation; custom code
would only add surface.

## Evidence

- 2026-09-20 (uncommitted working tree): `app_quimico/tests/test_password_change.py`
  9 passed; full suite `pytest -q` 75 passed; `python manage.py check` no
  issues. T1-T3 done. No commit made (parent owns terminal git).

## Decisions / notes

- Order decision 2026-09-20: operator picked change-password first, MFA (T5 of
  p1-password-recovery) next.
- Review gate note: RDD is clone-local OFF in this repo (temporary, pi relay
  bug upstream); CI in GitHub Actions is the active safety net.
