"""Vistas de verificación en dos pasos (MFA/TOTP) con django-otp.

La app conserva su ``CustomLoginView`` (ver ``app_quimico.views``); este módulo
solo agrega los dos pasos propios del segundo factor:

* ``mfa_setup``: inscripción opcional. Reutiliza o crea un ``TOTPDevice`` sin
  confirmar, muestra el QR del URI ``otpauth://`` y confirma el primer código.
* ``mfa_verify``: segundo paso del login para usuarios ya inscritos. Verifica
  el código y marca la sesión como verificada con ``django_otp.login``.

El QR se genera server-side con la fábrica SVG de ``qrcode`` (sin Pillow).
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
from django_otp.plugins.otp_totp.models import TOTPDevice

DEFAULT_DEVICE_NAME = "Authenticator"
SETUP_TEMPLATE = "app_quimico/autenticacion/mfa_setup.html"
VERIFY_TEMPLATE = "app_quimico/autenticacion/mfa_verify.html"


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


def _confirmed_device(user):
    """Dispositivo TOTP confirmado del usuario, o ``None``."""
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


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
    """Inscripción opcional en MFA: QR + confirmación del primer código."""
    if _confirmed_device(request.user) is not None:
        return render(request, SETUP_TEMPLATE, {"already_enrolled": True})

    device = _pending_device(request.user)
    form = TokenForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["token"]):
            device.confirmed = True
            device.save()
            messages.success(
                request, "¡Listo! La verificación en dos pasos quedó activada."
            )
            return redirect("perfil_personal")
        form.add_error("token", "El código no es válido o ya expiró. Inténtalo de nuevo.")

    context = {
        "form": form,
        "already_enrolled": False,
        "provisioning_uri": device.config_url,
        "qr_svg": _provisioning_qr_svg(device.config_url),
    }
    return render(request, SETUP_TEMPLATE, context)


@login_required
def mfa_verify(request):
    """Segundo paso del login: valida el código y marca la sesión verificada."""
    device = _confirmed_device(request.user)
    if device is None or request.user.is_verified():
        # Sin dispositivo confirmado no hay nada que verificar; si ya está
        # verificado, no se repite el paso.
        return redirect(_login_redirect_url(request))

    form = TokenForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        if device.verify_token(form.cleaned_data["token"]):
            otp_login(request, device)
            messages.success(
                request,
                f"¡Bienvenido(a) de nuevo, {request.user.username}! "
                "Has iniciado sesión con éxito.",
            )
            return redirect(_login_redirect_url(request))
        form.add_error("token", "El código no es válido o ya expiró. Inténtalo de nuevo.")

    return render(request, VERIFY_TEMPLATE, {"form": form})
