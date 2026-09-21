# p1-mfa-self-rebind

**Status:** DONE (commiteado: 463d2ea; pendiente push con decisión del operador)

## Goal

Re-vinculación propia del authenticator (self-rebind): un usuario cuya sesión está **verificada** (pasó el segundo factor en esta sesión — TOTP o código de respaldo) puede re-configurar su propio MFA desde la web sin depender del admin. Cierre del ciclo "perdí mi celu": rescate con backup code → re-enrolamiento fresco → códigos viejos invalidados.

## Contexto de la sesión previa (exploración ya realizada)

- `mfa_setup` (mfa_views.py): si hay TOTPDevice confirmed → renderiza `already_enrolled=True` (rama del template mfa_setup.html L11-33, solo mensaje + "Volver a mi perfil"). Ahí entra el rebind.
- `_pending_device` reutiliza/crea un TOTPDevice unconfirmed (name="Authenticator", confirmed=False) — puede haber restos de enrolamientos abortados.
- `_static_device` / `_generate_backup_codes(device, n=10)` ya existen (p1-mfa-backup-codes, commit 66e65ba): invalidar códigos = `device.token_set.all().delete()`.
- `request.user.is_verified()` (django-otp) es True solo si la sesión pasó `otp_login` con algún device — es el gate de seguridad del rebind.
- Convenciones: FBV `@login_required`, crispy/bootstrap5, card shadow, messages, tests con fixtures + login HTTP POST + `_reset_axes_attempts`.

## Decisiones de diseño (acordadas con el operador)

1. **El rebind exige sesión verificada**: el botón solo aparece si `already_enrolled AND request.user.is_verified()`. Un secuestrador con solo contraseña (primera factor) NO puede reemplazar silenciosamente el authenticator. Si no está verificada, la página ya-enrolado muestra el mensaje actual sin opción.
2. **El rebind borra TODOS los TOTPDevice del usuario** (confirmados y unconfirmed, restos de setups abortados) y arranca el flujo fresco (QR nuevo → confirmación).
3. **El rebind invalida automáticamente los códigos de respaldo** existentes (borra los StaticToken del StaticDevice; el StaticDevice se reutiliza). Mensaje claro: "tus códigos de respaldo anteriores fueron invalidados, generá un set nuevo".
4. La acción es POST con `confirm()` en el submit — nunca un GET destructivo.
5. Después del rebind exitoso (confirmación del device nuevo), el usuario queda enrolado normal; puede generar códigos nuevos en `mfa_backup_codes`.

## Tasks

- [x] T1 `mfa_views.py`: en `mfa_setup`, en la rama `already_enrolled`: si `request.user.is_verified()`, aceptar POST de reconfiguración (`action=reconfigure` en el form): con confirm, borrar todos los TOTPDevice del usuario, invalidar StaticTokens (si StaticDevice existe), limpiar device pendiente, y seguir el flujo normal (crear pending device + render QR en la misma respuesta). Si no está verificado, solo el mensaje actual. Mensajes de éxito/invalidación.
- [x] T2 `mfa_setup.html`: en la rama ya-enrolado, si `can_reconfigure` (nuevo flag de contexto), mostrar card/botón "Re-configurar autenticador" (POST, `confirm('...invalidará tu authenticator actual y tus códigos de respaldo...')`) + texto explicativo de por qué está disponible (sesión verificada).
- [x] T3 Tests `app_quimico/tests/test_mfa_self_rebind.py`: rebind exitoso (borra devices viejos, crea pending, QR presente, códigos invalidados StaticToken.count()==0), rebind exige sesión verificada (login + TOTP NO verificado → sin botón/POST rechazado), usuario ya enrolado sin verificar → sin opción, rebind limpia unconfirmed devices restantes, confirmación del device nuevo funciona end-to-end (verify token → confirmed), perfil no cambia. Patrones: fixtures + HTTP POST login + `_reset_axes_attempts`; generar token TOTP como en test_mfa_totp (django_otp.oath.totp).
- [x] T4 Docs: README sección MFA (re-configurar autenticador) + esta evidencia.

## Evidence

### Cambios por archivo

- `app_quimico/mfa_views.py`:
  - `mfa_setup`: la rama `already_enrolled` calcula `can_reconfigure = request.user.is_verified()` y solo ejecuta el rebind con `request.method == "POST"` y `action == "reconfigure"` (nunca por GET). En ese caso borra `TOTPDevice.objects.filter(user=...)` (confirmados + restos sin confirmar), invalida códigos de respaldo y cae al flujo fresco (`_pending_device` + QR) en la misma respuesta. Mensaje success ("Re-configuraste tu autenticador…") y warning ("códigos de respaldo anteriores fueron invalidados…") condicionado a que existieran códigos.
  - Nuevo helper `_invalidate_backup_codes(user)`: si hay `StaticToken` del usuario, reutiliza `_static_device(user)` (decisión #3) y borra sus tokens; devuelve si había algo que invalidar.
  - Confirmación en el flujo fresco: se agregó `otp_login(request, device)` al confirmar un token válido (ver Desviaciones).
- `app_quimico/templates/app_quimico/autenticacion/mfa_setup.html`: en la rama ya-enrolado, si `can_reconfigure`, card `shadow mt-4` con texto (sesión verificada) + alert warning + form POST (`action=reconfigure`) con `onclick="return confirm('…')"` y botón `btn-outline-danger` "Re-configurar autenticador". Se conserva el link "Volver a mi perfil".
- `app_quimico/tests/test_mfa_self_rebind.py`: 10 tests nuevos (pytestmark django_db, `_reset_axes_attempts` autouse, fixtures `user`/`confirmed_device`/`backup_codes`/`verified_client`, login HTTP POST, tokens con `django_otp.oath.totp`).
- `README.md`: bullet de self-rebind en "Autenticación y recuperación" + contadores 125→136 ejecuciones / 108→131 tests.
- `odd/tasks/p1-mfa-self-rebind.md`: tasks marcadas y evidencia.

### Verificación (observada)

- `pytest app_quimico -q` → **136 passed** (baseline 126 + 10 nuevos). `app_quimico/tests/test_mfa_self_rebind.py` → **10 passed**.
- `python manage.py check` → System check identified no issues (0 silenced).
- `python manage.py makemigrations --check` → No changes detected.

### Desviaciones

1. **`otp_login` en la confirmación del enrolamiento fresco.** Al reemplazar el autenticador, la clave de sesión apunta al device borrado y `OTPMiddleware` la descarta, dejando la sesión sin verificar. Para que la confirmación del device nuevo deje la sesión verificada (T3-4), `mfa_setup` marca `otp_login(request, device)` sobre el token válido. Es correcto también en el enrolamiento inicial: el usuario acaba de probar posesión del factor. No se tocó el gate de login (`views.py`) ni el paso `mfa_verify`.
2. **Mensaje de invalidación condicionado.** Solo se muestra si había códigos de respaldo, para no afirmar una invalidación inexistente ni crear un `StaticDevice` vacío.

## Notes

- Sin cambios en settings ni migraciones (no hay apps ni modelos nuevos).
- Sin cambios en el gate de login (`views.py:106`) — el rebind no altera el flujo del segundo paso.
- Verificar que el mensaje del flujo normal ("MFA activado") no entre en conflicto con los mensajes del rebind.
- Work-unit commit: `463d2ea feat(auth): re-configuración propia del autenticador MFA con sesión verificada` (4 archivos, +356/-5). Validado por el operador en local (flujo completo: card, confirmación, QR nuevo, aviso de invalidación).

## Verificación independiente (gentle-ai-verify)

- PASS 7/7: suite 136 passed; check y makemigrations --check limpios; reconfigure POST-only + gate is_verified; borrado solo de devices del usuario; StaticToken borrados pero StaticDevice preservado; sin verificación no se borra nada (early-return antes del delete); desviación otp_login en confirmación auditada y segura (el confirm exige token correcto; gate de login y mfa_verify intactos); template gated por can_reconfigure con csrf y confirm() completo; tests no vacuos (unverified no-op y end-to-end is_verified); sin cambios fuera de superficie.
- Notas no bloqueantes: (a) _invalidate_backup_codes con StaticDevice unconfirmed ajeno al flujo (solo posible vía admin) podría dejar tokens y mensaje falso — severidad baja; (b) usuario verificado que abandona el rebind sin confirmar queda sin MFA hasta re-enrolar — estado auto-infligido, no bypass.
