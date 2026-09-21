"""Self-rebind MFA tests (re-configuración propia del autenticador).

Cubre el cierre del ciclo "perdí mi celu": un usuario con la sesión ya
**verificada** (segundo factor superado) puede re-configurar su propio
autenticador desde ``mfa_setup`` con un POST ``action=reconfigure``. El rebind
borra sus dispositivos TOTP, invalida los códigos de respaldo existentes y
continúa con el enrolamiento fresco (QR nuevo) en la misma respuesta.

El rebind exige la sesión verificada: un secuestrador con solo la contraseña
(primer factor) no puede reemplazar silenciosamente el autenticador.

Login en tests vía HTTP POST a la ruta de login porque django-axes rechaza el
helper directo ``client.login()`` (mismo patrón que ``test_mfa_totp.py``).
Los tokens TOTP se generan con ``django_otp.oath`` a partir de la clave del
propio dispositivo.
"""

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
RECONFIGURE_BUTTON = "Re-configurar autenticador"


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="quimico", password=PASSWORD, email="quimico@correo.com"
    )


@pytest.fixture
def confirmed_device(user):
    return TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=True)


@pytest.fixture
def backup_codes(user):
    """Seed a StaticDevice with three backup codes for the user."""
    device = StaticDevice.objects.create(
        user=user, name="Backup Code", confirmed=True
    )
    return [
        StaticToken.objects.create(device=device, token=f"codigo{i:04d}")
        for i in range(3)
    ]


@pytest.fixture
def verified_client(client, user, confirmed_device):
    """Logged-in client whose session already passed the second factor."""
    _login(client, user)
    response = client.post(
        reverse("mfa_verify"), data={"token": _token(confirmed_device)}
    )
    assert response.status_code == 302
    assert client.session[DEVICE_ID_SESSION_KEY] == confirmed_device.persistent_id
    return client


def _token(device, drift=0):
    """Current token for ``device``, generated from its own secret."""
    value = totp(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift + drift,
    )
    return f"{value:06d}"


def _login(client, user):
    """HTTP-POST login (primer factor)."""
    return client.post(
        reverse("login"), data={"username": user.username, "password": PASSWORD}
    )


def _reconfigure(client):
    """POST the destructive rebind action."""
    return client.post(reverse("mfa_setup"), data={"action": "reconfigure"})


# --- Successful rebind (verified session) ---


def test_rebind_requires_login(client):
    response = client.post(reverse("mfa_setup"), data={"action": "reconfigure"})

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_rebind_deletes_devices_invalidates_codes_and_renders_new_qr(
    verified_client, user, confirmed_device, backup_codes
):
    old_device_id = confirmed_device.pk

    response = _reconfigure(verified_client)

    assert response.status_code == 200
    assert response.context["already_enrolled"] is False
    assert not response.context["form"].errors  # el POST de rebind no ensucia el form del QR

    content = response.content.decode()
    assert "<svg" in content  # nuevo QR inline
    assert "otpauth://totp/" in content
    assert "fueron invalidados" in content

    # El dispositivo confirmado anterior se borró y se creó un pendiente nuevo.
    assert TOTPDevice.objects.filter(user=user, confirmed=True).count() == 0
    pending = TOTPDevice.objects.get(user=user)
    assert pending.confirmed is False
    assert pending.pk != old_device_id

    # Los códigos de respaldo quedaron invalidados; el StaticDevice se reutiliza.
    assert StaticToken.objects.filter(device__user=user).count() == 0
    assert StaticDevice.objects.filter(user=user).count() == 1


def test_rebind_cleans_stale_unconfirmed_devices_too(
    verified_client, user, confirmed_device
):
    stale = TOTPDevice.objects.create(
        user=user, name="Authenticator", confirmed=False
    )

    _reconfigure(verified_client)

    devices = list(TOTPDevice.objects.filter(user=user))
    assert len(devices) == 1  # solo el pendiente nuevo
    assert devices[0].confirmed is False
    assert devices[0].pk not in {confirmed_device.pk, stale.pk}


def test_rebind_without_backup_codes_has_no_invalidation_message(
    verified_client, user, confirmed_device
):
    response = _reconfigure(verified_client)

    content = response.content.decode()
    assert "Re-configuraste tu autenticador" in content
    assert "fueron invalidados" not in content
    # Sin códigos que invalidar no se crea un StaticDevice vacío.
    assert StaticDevice.objects.filter(user=user).exists() is False


def test_rebind_get_never_triggers_the_action(verified_client, user, confirmed_device):
    response = verified_client.get(reverse("mfa_setup") + "?action=reconfigure")

    assert response.status_code == 200
    assert response.context["already_enrolled"] is True
    assert RECONFIGURE_BUTTON in response.content.decode()
    # El GET no borra nada: el dispositivo confirmado sigue intacto.
    assert TOTPDevice.objects.filter(user=user, confirmed=True).count() == 1


# --- Rebind requires a verified session ---


def test_rebind_button_hidden_without_verified_session(client, user, confirmed_device):
    # Solo primer factor: la sesión queda autenticada pero sin verificar.
    _login(client, user)
    assert DEVICE_ID_SESSION_KEY not in client.session

    response = client.get(reverse("mfa_setup"))

    assert response.status_code == 200
    assert response.context["already_enrolled"] is True
    assert response.context["can_reconfigure"] is False
    assert RECONFIGURE_BUTTON not in response.content.decode()
    assert "ya está activada" in response.content.decode()


def test_reconfigure_post_rejected_without_verified_session(
    client, user, confirmed_device
):
    _login(client, user)

    response = _reconfigure(client)

    assert response.status_code == 200
    assert response.context["already_enrolled"] is True
    assert RECONFIGURE_BUTTON not in response.content.decode()

    # Los dispositivos quedan intactos: el POST fue un no-op.
    assert TOTPDevice.objects.filter(user=user, confirmed=True).count() == 1
    confirmed_device.refresh_from_db()
    assert confirmed_device.confirmed is True


def test_unverified_rebind_keeps_backup_codes(client, user, confirmed_device, backup_codes):
    _login(client, user)

    _reconfigure(client)

    assert StaticToken.objects.filter(device__user=user).count() == len(backup_codes)


# --- End-to-end enrolment after rebind ---


def test_rebind_new_device_can_be_confirmed_end_to_end(
    verified_client, user, confirmed_device
):
    _reconfigure(verified_client)
    pending = TOTPDevice.objects.get(user=user)

    response = verified_client.post(
        reverse("mfa_setup"), data={"token": _token(pending)}
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")
    pending.refresh_from_db()
    assert pending.confirmed is True

    final = verified_client.get(response["Location"])
    assert final.wsgi_request.user.is_verified() is True
    assert final.wsgi_request.user.otp_device.persistent_id == pending.persistent_id


def test_rebind_keeps_profile_data(verified_client, user, confirmed_device):
    # El rebind no toca datos de perfil ni el username.
    before = (user.username, user.email)

    _reconfigure(verified_client)

    user.refresh_from_db()
    assert (user.username, user.email) == before
    assert verified_client.get(reverse("perfil_personal")).status_code == 200
