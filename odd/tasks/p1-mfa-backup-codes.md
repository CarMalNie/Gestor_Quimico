# p1-mfa-backup-codes

**Status:** DONE — commit 66e65ba en origin/main, desplegado en producción.

## Goal

Códigos de respaldo MFA (backup codes) con `otp_static` (StaticDevice + StaticToken): el usuario puede generar 10 códigos de un solo uso después de enrolar TOTP, y usarlos en el segundo paso del login cuando no tiene su authenticator. Responde al problema validado: pérdida/borrado del dispositivo TOTP.

## Contexto establecido en la exploración

- django-otp 1.7.3 ya instalado; `otp_static` es plugin incluido (StaticDevice, StaticToken, migraciones propias, admin auto-registrado). No requiere modelo propio ni migration de app_quimico.
- Token estático: 8 caracteres base32 minúsculas (`random_token()`); `StaticDevice.verify_token` CONSUME el token al acertar (delete) y resetea throttle; en fallo incrementa throttle propio (factor default 1).
- `TokenForm.clean_token` actual rechaza no-dígitos → incompatibilidad con códigos base32; usar un form separado para backup codes.
- Gate del segundo paso: `views.py` CustomLoginView redirige a `mfa_verify` solo si hay TOTPDevice confirmed; `mfa_verify` además redirige si `device is None`.
- `match_token()` (sweep de todos los devices) está desaconsejado por django-otp (throttling); verificar contra el StaticDevice específico.
- `mfa_setup` confirma el device sin llamar `otp_login` — seguir ese patrón.
- Tests: pytest + fixtures (`user`, `logged_client`, `confirmed_device`, `_login` por HTTP POST, `_reset_axes_attempts`); login por POST porque axes bloquea `client.login()`.
- Convencciones: vistas FBV con `@login_required`, crispy/bootstrap5, card shadow, `{% url %}`, mensajes via `messages`.

## Decisiones de diseño (acordadas con el operador)

1. **Backup codes = fallback, no factor independiente**: requieren un TOTPDevice confirmed para generarse; el gate del segundo paso sigue siendo TOTP-driven (StaticDevice solo no fuerza el segundo paso). Rationale: los códigos existen como recuperación del authenticator, no como reemplazo.
2. **Regeneración invalida los anteriores**: regenerar borra los StaticToken previos y crea un set nuevo (one-way).
3. **Generación solo con TOTP enrolado** (confirmado); si no, redirige con mensaje.
4. Los códigos se muestran **una sola vez** (plaintext en la respuesta de generación, nunca re-listados).
5. OTP_STATIC_THROTTLE_FACTOR default (no se agrega setting); tokens visibles en admin (sin OTP_ADMIN_HIDE_SENSITIVE_DATA) — anotado, no acciona.

## Tasks

- [x] T1 Settings: agregar `django_otp.plugins.otp_static` a INSTALLED_APPS (tras otp_totp) + comentario; sin migration nueva de app.
- [x] T2 Helpers en mfa_views.py: `_static_device(user)` (get-or-create, name="Backup Code", confirmed=True), `_generate_backup_codes(device, n=10)` (borra previos, crea 10 StaticToken, devuelve plaintext list), `_consume_backup_code(user, code)` (verifica contra StaticDevice del usuario, respeta one-time).
- [x] T3 Vistas/rutas: vista `mfa_backup_codes` (GET: estado/última generación; POST: generar/regenerar, muestra los códigos una sola vez con advertencia; requiere TOTP confirmed, si no redirige a mfa_setup con mensaje) + fallback en `mfa_verify`: form/alternativa que acepte código de respaldo (base32) verificando contra StaticDevice y llamando `otp_login(request, static_device)`. URL names: `mfa_backup_codes` (+ ancla o modo en `mfa_verify`).
- [x] T4 Templates: template de generación (card, códigos en grid, aviso one-time, botón regenerar con confirmación); entrada "usar código de respaldo" en `mfa_verify.html` (link/alternativa que relaja el form a base32); botón "Códigos de respaldo" en perfil_personal.html junto a MFA setup.
- [x] T5 Tests `app_quimico/tests/test_mfa_backup_codes.py`: generación (10 códigos, invalida anteriores), consumo one-time (segundo uso falla), verificación fallback marca sesión verificada (`is_verified()` + DEVICE_ID_SESSION_KEY), código incorrecto, sin TOTP enrolado (generación redirige), gate de login intacto (StaticDevice solo NO fuerza segundo paso), template muestra códigos una vez. Patrones: fixtures + HTTP POST login + axes reset.
- [x] T6 Docs: README secciones auth (L74 planificado → implementado; L165 roadmap) + esta evidencia.

## Evidence

- T1: `core/settings.py` agrega `'django_otp.plugins.otp_static'` inmediatamente después de `otp_totp`, con el comentario del bloque actualizado. `makemigrations --check` → "No changes detected".
- T2: `app_quimico/mfa_views.py` agrega `_static_device` (get-or-create confirmado), `_generate_backup_codes` (borra el set previo y crea 10 `StaticToken.random_token()`, devuelve plaintext) y `_consume_backup_code` (verifica contra el `StaticDevice` del usuario con `device.verify_token`, consumo one-time; sin `match_token`).
- T3: `mfa_backup_codes` (GET estado / POST genera+muestra una vez; redirige a `mfa_setup` con mensaje si no hay TOTP confirmado) y `mfa_verify` con `BackupCodeForm`, modo `?backup=1`, oferta automática tras fallo TOTP y `otp_login(request, static_device)` en éxito. Ruta `accounts/mfa/backup-codes/` name `mfa_backup_codes` en `urls.py`.
- T4: nuevo `mfa_backup_codes.html` (card shadow, grid de códigos, aviso "una única vez", regenerar con `confirm`), `mfa_verify.html` con link "¿Perdiste tu autenticador? Usa un código de respaldo" y form alternativo, `perfil_personal.html` con botón "Códigos de respaldo".
- T5: `app_quimico/tests/test_mfa_backup_codes.py` — 13 tests nuevos (todos verdes).
- T6: README actualizado (recuperación con autenticador perdido + códigos de respaldo implementados; roadmap marcado `[x]`; contadores de tests 112→125 / 95→108).
- Verificación: `pytest app_quimico -q` → **125 passed**; `manage.py check` → sin issues; `makemigrations --check` → sin cambios.
- Verificación independiente (gentle-ai-verify): PASS 7/7 — one-time corroborado en fuente django-otp (verify_token borra el token), fallback inaccesible sin TOTP confirmado, sin logging de códigos, csrf OK, gate intacto (test real con StaticDevice-only), sin cambios fuera de las superficies, sin deps/secretos nuevos.
- Work-unit commit: `66e65ba feat(auth): códigos de respaldo MFA de un solo uso con otp_static` (8 archivos, +556/-38).

## Notes

- Gate TOTP-only confirmado como decisión #1 — no cambia `views.py:106` ni el guard de `mfa_verify` respecto al gate; el guard `device is None` de mfa_verify solo aplica a usuarios SIN TOTP, que tampoco tendrán StaticDevice (generación lo impide), así que el bypass queda cerrado por diseño.
- `makemigrations --check` debe quedar limpio; CI corre migrate contra MySQL 8.
