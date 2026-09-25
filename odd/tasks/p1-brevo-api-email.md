# Feature: p1-brevo-api-email — gestor_quimico

Status: DONE — fully shipped to production (backend committed 57e461b with
T1–T4, pushed and deployed to PA; recovery emails send through the Brevo HTTP
API in production). Header closed 2026-09-25 in the stale-tracker housekeeping
(batch with p1-mfa-totp and p1-password-change).

Goal: send Django emails (password recovery) through the Brevo HTTP API
(`https://api.brevo.com/v3/smtp/email`), which is whitelisted on PythonAnywhere
free accounts, while keeping the existing SMTP path for local development.

Context established during exploration (do not re-explore from scratch):

- PA free tier: web apps reach the internet only through PA's proxy with an
  allowlist; `api.brevo.com` IS on the list (verified against
  pythonanywhere.com/whitelist/, 2026-09-20). Direct SMTP is blocked from web
  apps regardless of host (source: PA forums/staff).
- Production evidence: PA error log shows `ConnectionRefusedError [Errno 111]`
  when the web app tried smtp-relay.brevo.com:587; the `.env` IS read
  correctly (backend was already SMTP). Brevo SMTP credentials remain valid
  and are used locally.
- Django's `PasswordResetForm.send_mail` catches `smtplib.SMTPException` and
  logs "Failed to send password reset email" — a failing backend should raise
  a `smtplib.SMTPException` subclass to keep that graceful behavior (no 500
  for the user, failure visible in PA error log).
- Brevo API contract: `POST /v3/smtp/email`, header `api-key: <key>`, JSON
  body with `sender` {name, email}, `to`/`cc`/`bcc` lists of {email, name?},
  `subject`, `textContent`/`htmlContent`. Non-2xx returns error JSON.
- Use `urllib.request` from stdlib — NO new dependency (qrcode/django-otp were
  enough; requests is not currently pinned).

## Tasks

- [x] T1 Backend: new `app_quimico/brevo_api_backend.py` with
      `BrevoApiEmailBackend(BaseEmailBackend)`: builds the JSON payload from
      each `EmailMessage` (from_email split into name/email, recipients
      to/cc/bcc, subject, textContent for plain or htmlContent when
      `content_subtype == 'html'`), reads `EMAIL_API_KEY` via decouple (raises
      if missing when the backend is instantiated), POSTs with timeout,
      returns number of messages sent; on non-2xx response raises
      `smtplib.SMTPException` (with Brevo's error text) so Django's existing
      graceful handling applies. Attachments are out of scope (reset emails
      have none): if present, log a warning and still send the text.
- [x] T2 Settings wiring in `core/settings.py`: extend the existing
      selection logic — `EMAIL_API_KEY` set → Brevo API backend;
      elif `EMAIL_HOST` set → SMTP backend; else console. Update the
      explanatory comment. No behavior change when the key is absent.
- [x] T3 Tests in new `app_quimico/tests/test_brevo_api_email.py` (no real
      network — patch the HTTP call): success 2xx returns count and posts the
      expected URL/header/body (sender name+email from DEFAULT_FROM_EMAIL,
      recipients mapping, subject, text vs html content); non-2xx raises
      SMTPException; missing API key raises at construction; password-reset
      flow still uses `send_mail()` transparently (the backend is a drop-in).
- [x] T4 Docs: `.env.example` gains the `EMAIL_API_KEY` variant documented
      (Option B for PythonAnywhere free tier) next to the SMTP examples.
      Originally blocked for the worker (sensitive-path guard); applied by the
      operator/parent in commit 57e461b, verified in the current file (email
      option C block, lines 44–50).
- [x] T5 Close: full suite green (60 passed across the emails+MFA+password
      modules in the 2026-09-25 housekeeping re-check), work-unit commit 57e461b
      (Conventional Commit), evidence recorded; the operator added
      `EMAIL_API_KEY` to the PA `.env`, reloaded, and validated the production
      reset (accented sender fix followed in production, validated).

Rejected alternative: Paid PythonAnywhere plan (USD ~5/mo). Works today, but
costs money permanently and the API path also demonstrates external-service
integration in the portfolio.

Rejected alternative: sending from a custom PA-hosted SMTP relay of our own —
same outbound-SMTP block, more infrastructure.

## Evidence

- 2026-09-20 — T1–T3 implemented (uncommitted). Focused suite first:
  `.venv/Scripts/python.exe -m pytest app_quimico/tests/test_brevo_api_email.py -q`
  → 16 passed. Full authorized verification:
  `.venv/Scripts/python.exe manage.py check` → "System check identified no
  issues (0 silenced)."; `.venv/Scripts/python.exe -m pytest -q` → 112 passed
  (baseline before the change was 96 passed), 113.30s.
- Settings precedence verified by importing `core.settings` in three
  environments: default (`.env`: EMAIL_HOST set, no key) → SMTP backend,
  unchanged; `EMAIL_API_KEY` set → `app_quimico.brevo_api_backend.
  BrevoApiEmailBackend`; `EMAIL_BACKEND` set explicitly → that value wins.
- No live Brevo call was made: every test patches
  `app_quimico.brevo_api_backend.urllib.request.urlopen`.
- T4 applied 2026-09-20 by the orchestrator: `.env.example` gained the
  "Email option C - Brevo HTTP API" block (with the `EMAIL_API_KEY` example)
  right before the credentials warning. The worker's guard blocks reading
  and writing any `.env*` path, so the operator authorized a paste-based
  plan and the orchestrator applied it via a targeted replacement, verified
  by occurrence counts only (1 EMAIL_API_KEY line; credentials warning
  intact).
- 2026-09-20 57e461b feat(email): backend de envio por API HTTP de Brevo
  (T1-T4: BrevoApiEmailBackend con urllib stdlib, selección 3-vía en
  settings, 16 tests con HTTP mockeado; suite 112 passed; .env.example
  con la opción C). Verificación independiente gentle-ai-verify: PASS
  (seguridad: clave nunca logueada, errores mapeados a SMTPException,
  sin inyección; precedencia; tests; scope). Nota de rotación de la
  SMTP key commiteada aparte en c7c2767.

## Decisions / notes

- Option decision 2026-09-20: operator picked Option B over paying for PA.
- Brevo credentials: SMTP key (no-expiry) stays for local SMTP path; the new
  API key (name `gestor-quimico-pa`) is production-only, stored in PA `.env`
  by the operator, never committed, never passed through chat.
- The PA whitelist contains `api.brevo.com` (checked 2026-09-20). If PA ever
  drops it, the feature degrades to the SMTP error path already handled.
- Review gate note: RDD is clone-local OFF (temporary, pi relay bug upstream);
  CI in GitHub Actions is the active safety net.
- Implementation deviations from the T1 wording (all inside the approved
  surface, no scope change):
  - Payload building and the HTTP call are split: `_send(message)` returns the
    Brevo JSON payload and `_post(payload)` performs the single POST per
    message. Keeps the payload unit-testable without touching urllib.
  - The payload drops every falsy value, not only `None`: Brevo rejects null
    fields and empty `cc`/`bcc` lists, so an empty recipient list is omitted.
  - A whitespace-only `EMAIL_API_KEY` is treated as missing (stripped check) so
    a stray `EMAIL_API_KEY=   ` in `.env` fails loudly at construction instead
    of as a 401 at send time.
  - Network failures (DNS/refused/timeout, i.e. `OSError`/`URLError`) are also
    converted to `smtplib.SMTPException`, not just non-2xx responses: the
    reset flow must stay graceful when PA's proxy drops the connection.
  - Attachments: warning logged, body still sent, matching T1.
  - Tests go beyond the T3 list with four negative/alternate cases:
    `fail_silently=True` returns 0, network error mapping, empty recipient
    lists, and no-message input returning 0 without any POST.
- T4 ready-to-paste block (historical; the applied block in `.env.example`
  from commit 57e461b covers the same variant as "Email option C"):

```
# --- Opción B: API HTTP de Brevo (PythonAnywhere free no permite SMTP saliente) ---
# El web app sí alcanza api.brevo.com (lista blanca del proxy). Genera la key en
# el panel de Brevo: SMTP & API -> API Keys. Si se define, gana sobre EMAIL_HOST.
# EMAIL_API_KEY=
```

- Harness note (historical): the safety guard rejected any read of
  `.env.example` (`sensitive path`) at worker time, so T4 was applied later by
  the parent/operator inside 57e461b and verified in the file.
