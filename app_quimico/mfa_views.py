"""Vistas de verificación en dos pasos (MFA/TOTP) con django-otp.

La app conserva su ``CustomLoginView`` (ver ``app_quimico.views``); este módulo
solo agrega los dos pasos propios del segundo factor:

* ``mfa_setup``: inscripción opcional. Reutiliza o crea un ``TOTPDevice`` sin
  confirmar, muestra el QR del URI ``otpauth://`` y confirma el primer código.
* ``mfa_verify``: segundo paso del login para usuarios ya inscritos. Verifica
  el código y marca la sesión como verificada con ``django_otp.login``.

El QR se genera server-side con la fábrica SVG de ``qrcode`` (sin Pillow).

Además de TOTP, ``mfa_backup_codes`` genera códigos de respaldo de un solo uso
(``otp_static``) y ``mfa_verify`` acepta uno de ellos como alternativa cuando el
usuario perdió su autenticador. Los códigos son un respaldo del segundo factor,
no un factor independiente: requieren un ``TOTPDevice`` ya confirmado.

Cierre del ciclo "perdí mi celu": un usuario con la sesión ya verificada puede
re-configurar su propio autenticador desde ``mfa_setup`` (POST
``action=reconfigure``). El rebind exige la sesión verificada, borra sus
dispositivos TOTP, invalida los códigos de respaldo existentes y continúa con un
enrolamiento fresco en la misma respuesta.
"""

import io

import qrcode
import qrcode.image.svg
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from app_quimico.middleware import ADMIN_GROUP_NAME

DEFAULT_DEVICE_NAME = "Authenticator"
BACKUP_DEVICE_NAME = "Backup Code"
BACKUP_CODE_COUNT = 10
SETUP_TEMPLATE = "app_quimico/autenticacion/mfa_setup.html"
VERIFY_TEMPLATE = "app_quimico/autenticacion/mfa_verify.html"
BACKUP_TEMPLATE = "app_quimico/autenticacion/mfa_backup_codes.html"


class TokenForm(forms.Form):
    """Campo único para el código TOTP de 6 dígitos que comparten ambos pasos."""

    token = forms.CharField(
        label="Código de verificación",
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "autofocus": True,
                "placeholder": "123456",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data["token"].strip().replace(" ", "")
        if not token.isdigit():
            raise forms.ValidationError("El código debe contener solo números.")
        return token


class BackupCodeForm(forms.Form):
    """Campo para un código de respaldo base32 (``otp_static``).

    Es un formulario separado de :class:`TokenForm` porque los códigos de
    respaldo no son numéricos: ``TokenForm.clean_token`` los rechazaría.
    """

    backup_code = forms.CharField(
        label="Código de respaldo",
        max_length=16,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "autofocus": True,
                "placeholder": "a1b2c3d4e5",
            }
        ),
    )

    def clean_backup_code(self):
        code = self.cleaned_data["backup_code"].strip().lower().replace(" ", "")
        if not code:
            raise forms.ValidationError("Ingresa un código de respaldo.")
        return code


def _confirmed_device(user):
    """Dispositivo TOTP confirmado del usuario, o ``None``."""
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def _mfa_obligatorio_pendiente(user):
    """``True`` si el usuario debe MFA por política y aún no tiene TOTP confirmado.

    Alimenta el flag de plantilla homónimo que oculta el enlace "Volver a mi
    perfil": mientras ``ForceMFAAdminMiddleware`` bloquea la navegación de un
    Administrador sin MFA, ese enlace solo redirigiría de vuelta a esta misma
    página (callejón sin salida visual). Fuera de esa situación el enlace se
    mantiene.
    """
    return (
        user.groups.filter(name=ADMIN_GROUP_NAME).exists()
        and not TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    )


def _static_device(user):
    """Dispositivo estático (códigos de respaldo) confirmado, get-or-create.

    Se crea confirmado desde el inicio: los códigos no usan un paso de
    inscripción con QR, por lo que no hay nada que verificar al crearlo.
    """
    device = StaticDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        device = StaticDevice.objects.create(
            user=user, name=BACKUP_DEVICE_NAME, confirmed=True
        )
    return device


def _generate_backup_codes(device, n=BACKUP_CODE_COUNT):
    """Reemplaza los tokens de ``device`` por ``n`` códigos nuevos.

    La regeneración invalida por completo el set anterior (one-way): primero
    borra los ``StaticToken`` existentes y luego crea los nuevos. Devuelve la
    lista de códigos en texto plano, que solo puede mostrarse una vez.
    """
    device.token_set.all().delete()
    codes = []
    for _ in range(n):
        code = StaticToken.random_token()
        StaticToken.objects.create(device=device, token=code)
        codes.append(code)
    return codes


def _consume_backup_code(user, code):
    """Consume un código de respaldo del usuario y devuelve su ``StaticDevice``.

    Verifica contra el ``StaticDevice`` específico del usuario (no con
    ``django_otp.match_token``, desaconsejado por su sweep de dispositivos) para
    respetar el throttling propio del dispositivo. ``verify_token`` consume el
    token acertado, por lo que cada código sirve una sola vez. Devuelve ``None``
    si el usuario no tiene dispositivo o el código no es válido.
    """
    device = StaticDevice.objects.filter(user=user, confirmed=True).first()
    if device is None:
        return None
    if device.verify_token(code):
        return device
    return None


def _invalidate_backup_codes(user):
    """Invalida los códigos de respaldo existentes del usuario.

    Borra los ``StaticToken`` del ``StaticDevice`` reutilizando el dispositivo
    (decisión de diseño #3 del rebind): el ``StaticDevice`` se conserva para que
    el usuario genere un set nuevo. Devuelve ``True`` cuando había códigos que
    invalidar.
    """
    if not StaticToken.objects.filter(device__user=user).exists():
        return False
    _static_device(user).token_set.all().delete()
    return True


def _pending_device(user):
    """Reutiliza el dispositivo sin confirmar del usuario o crea uno nuevo."""
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if device is None:
        device = TOTPDevice.objects.create(
            user=user, name=DEFAULT_DEVICE_NAME, confirmed=False
        )
    return device


def _provisioning_qr_svg(data):
    """Renderiza ``data`` (el URI ``otpauth://``) como SVG inline."""
    image = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    svg = buffer.getvalue().decode("utf-8")
    # La declaración XML no es válida al incrustar el SVG dentro del HTML.
    return svg.split("?>", 1)[-1].strip() if svg.startswith("<?xml") else svg


def _login_redirect_url(request):
    """Destino tras verificar: ``?next=`` válido o ``LOGIN_REDIRECT_URL``.

    ``LOGIN_REDIRECT_URL`` apunta al nombre de ruta ``perfil_personal``; se
    resuelve con ``resolve_url`` igual que hace ``LoginView``.
    """
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, {request.get_host()}, request.is_secure()
    ):
        return next_url
    return resolve_url(settings.LOGIN_REDIRECT_URL)


@login_required
def mfa_setup(request):
    """Inscripción opcional en MFA: QR + confirmación del primer código.

    Si el usuario ya tiene un dispositivo confirmado, la página solo muestra su
    estado. Un usuario con la **sesión verificada** (ya superó el segundo factor)
    puede re-configurar su autenticador con un POST ``action=reconfigure``:
    se borran sus dispositivos TOTP y los códigos de respaldo, y la misma
    respuesta continúa con el enrolamiento fresco (QR nuevo).
    """
    reconfigured = False
    if _confirmed_device(request.user) is not None:
        can_reconfigure = request.user.is_verified()
        is_reconfigure = (
            request.method == "POST"
            and request.POST.get("action") == "reconfigure"
        )
        if not (can_reconfigure and is_reconfigure):
            # Sin sesión verificada (o sin POST válido) no hay rebind: solo
            # estado. La acción destructiva nunca es alcanzable por GET.
            return render(
                request,
                SETUP_TEMPLATE,
                {
                    "already_enrolled": True,
                    "can_reconfigure": can_reconfigure,
                    "mfa_obligatorio_pendiente": _mfa_obligatorio_pendiente(
                        request.user
                    ),
                },
            )

        # Rebind: se eliminan todos los TOTPDevice (confirmados y restos
        # sin confirmar de setups abortados) y se invalidan los códigos de
        # respaldo existentes; se sigue con el flujo fresco de abajo.
        TOTPDevice.objects.filter(user=request.user).delete()
        invalidated_backup_codes = _invalidate_backup_codes(request.user)
        messages.success(
            request,
            "Re-configuraste tu autenticador. Escaneá el nuevo código QR y "
            "confirmalo con el código de 6 dígitos.",
        )
        if invalidated_backup_codes:
            messages.warning(
                request,
                "Tus códigos de respaldo anteriores fueron invalidados: "
                "generá un set nuevo cuando confirmes el nuevo autenticador.",
            )
        reconfigured = True

    device = _pending_device(request.user)
    # El POST de rebind no trae token: se renderiza el formulario sin atar para
    # no mostrar un error de campo obligatorio en el QR nuevo.
    if reconfigured:
        form = TokenForm()
    else:
        form = TokenForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["token"]):
            device.confirmed = True
            device.save()
            # El usuario acaba de probar posesión del factor: la sesión queda
            # verificada. Es lo que mantiene la sesión válida tras un rebind,
            # donde el dispositivo anterior se eliminó y su clave de sesión ya
            # no resuelve a ningún device (el middleware la descarta).
            otp_login(request, device)
            messages.success(
                request, "¡Listo! La verificación en dos pasos quedó activada."
            )
            return redirect("perfil_personal")
        form.add_error("token", "El código no es válido o ya expiró. Inténtalo de nuevo.")

    context = {
        "form": form,
        "already_enrolled": False,
        "can_reconfigure": False,
        "provisioning_uri": device.config_url,
        "qr_svg": _provisioning_qr_svg(device.config_url),
        "mfa_obligatorio_pendiente": _mfa_obligatorio_pendiente(request.user),
    }
    return render(request, SETUP_TEMPLATE, context)


@login_required
def mfa_verify(request):
    """Segundo paso del login: valida el código y marca la sesión verificada.

    Acepta el código TOTP habitual o, como alternativa cuando el usuario perdió
    su autenticador, un código de respaldo de un solo uso. El camino de respaldo
    se ofrece con ``?backup=1`` o después de un intento TOTP fallido.
    """
    device = _confirmed_device(request.user)
    if device is None or request.user.is_verified():
        # Sin dispositivo confirmado no hay nada que verificar; si ya está
        # verificado, no se repite el paso.
        return redirect(_login_redirect_url(request))

    form = TokenForm()
    backup_form = BackupCodeForm()
    show_backup = request.GET.get("backup") == "1"

    if request.method == "POST":
        if "backup_code" in request.POST:
            show_backup = True
            backup_form = BackupCodeForm(request.POST)
            if backup_form.is_valid():
                static_device = _consume_backup_code(
                    request.user, backup_form.cleaned_data["backup_code"]
                )
                if static_device is not None:
                    otp_login(request, static_device)
                    messages.success(
                        request,
                        f"¡Bienvenido(a) de nuevo, {request.user.username}! "
                        "Has iniciado sesión con un código de respaldo.",
                    )
                    return redirect(_login_redirect_url(request))
                backup_form.add_error(
                    "backup_code",
                    "El código de respaldo no es válido o ya fue usado.",
                )
        else:
            form = TokenForm(request.POST)
            if form.is_valid():
                if device.verify_token(form.cleaned_data["token"]):
                    otp_login(request, device)
                    messages.success(
                        request,
                        f"¡Bienvenido(a) de nuevo, {request.user.username}! "
                        "Has iniciado sesión con éxito.",
                    )
                    return redirect(_login_redirect_url(request))
                form.add_error(
                    "token", "El código no es válido o ya expiró. Inténtalo de nuevo."
                )
                # El código TOTP no funcionó: se ofrece el camino de respaldo.
                show_backup = True

    return render(
        request,
        VERIFY_TEMPLATE,
        {"form": form, "backup_form": backup_form, "show_backup": show_backup},
    )


@login_required
def mfa_backup_codes(request):
    """Genera y muestra una única vez los códigos de respaldo del usuario.

    Requiere un ``TOTPDevice`` confirmado: los códigos son un respaldo del
    segundo factor, no un factor independiente. En ``GET`` solo se muestra el
    estado; en ``POST`` se (re)generan 10 códigos y se muestran en texto plano
    únicamente en esa respuesta.
    """
    if _confirmed_device(request.user) is None:
        messages.error(
            request,
            "Activa primero la verificación en dos pasos (MFA) para poder "
            "generar códigos de respaldo.",
        )
        return redirect("mfa_setup")

    codes = None
    has_codes = StaticToken.objects.filter(device__user=request.user).exists()

    if request.method == "POST":
        device = _static_device(request.user)
        codes = _generate_backup_codes(device)
        has_codes = True
        messages.success(
            request,
            "Se generaron nuevos códigos de respaldo. Los códigos anteriores "
            "ya no son válidos.",
        )

    return render(
        request,
        BACKUP_TEMPLATE,
        {"codes": codes, "has_codes": has_codes},
    )
