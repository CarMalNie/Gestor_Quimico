"""Backup-code MFA tests (django-otp ``otp_static``).

Covers generation/regeneration of single-use backup codes, their use as a
fallback in the login second step, the TOTP-based login gate (a StaticDevice
alone must NOT force the second step) and the profile entry point.

Login in tests goes through HTTP POST to the login route because django-axes
rejects the direct ``client.login()`` helper (same pattern as
``test_mfa_totp.py``).
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
def logged_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def confirmed_device(user):
    return TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=True)


@pytest.fixture
def static_device(user):
    return StaticDevice.objects.create(user=user, name="Backup Code", confirmed=True)


def _login(client, user, next_url=None):
    """HTTP-POST login. ``next_url`` mirrors a ``?next=`` on the login request."""
    url = reverse("login")
    if next_url is not None:
        url = f"{url}?next={next_url}"
    return client.post(url, data={"username": user.username, "password": PASSWORD})


def _generate_codes(client):
    """POST to the backup-codes view and return the plaintext codes shown."""
    response = client.post(reverse("mfa_backup_codes"))
    assert response.status_code == 200
    return response.context["codes"]


def _invalid_totp(device):
    """Deterministic TOTP code outside the device tolerance window."""
    window = {
        totp(
            device.bin_key,
            step=device.step,
            t0=device.t0,
            digits=device.digits,
            drift=delta,
        )
        for delta in range(-2, 3)
    }
    candidate = 0
    while candidate in window:
        candidate += 1
    return f"{candidate:06d}"


# --- Generation page (mfa_backup_codes) ---


def test_backup_codes_requires_login(client):
    response = client.get(reverse("mfa_backup_codes"))

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_backup_codes_without_confirmed_totp_redirects_to_setup(logged_client):
    response = logged_client.get(reverse("mfa_backup_codes"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("mfa_setup")
    assert "Activa primero la verificación en dos pasos" in response.content.decode()


def test_backup_codes_status_without_codes(logged_client, confirmed_device):
    response = logged_client.get(reverse("mfa_backup_codes"))

    assert response.status_code == 200
    assert response.context["codes"] is None
    assert response.context["has_codes"] is False
    assert "Todavía no tienes códigos de respaldo" in response.content.decode()


def test_backup_codes_post_generates_ten_codes(logged_client, confirmed_device, user):
    response = logged_client.post(reverse("mfa_backup_codes"))

    codes = response.context["codes"]
    assert len(codes) == 10
    assert StaticToken.objects.filter(device__user=user).count() == 10
    assert StaticDevice.objects.filter(user=user, confirmed=True).exists()

    content = response.content.decode()
    assert "una única vez" in content
    for code in codes:
        assert code in content


def test_backup_codes_generation_invalidates_the_previous_set(
    logged_client, confirmed_device, user
):
    old_codes = _generate_codes(logged_client)
    new_codes = _generate_codes(logged_client)

    assert len(new_codes) == 10
    assert StaticToken.objects.filter(device__user=user).count() == 10
    assert StaticToken.objects.filter(token__in=old_codes).exists() is False
    stored = set(StaticToken.objects.filter(device__user=user).values_list("token", flat=True))
    assert stored == set(new_codes)


def test_backup_codes_page_shows_codes_on_generation_response_only(
    logged_client, confirmed_device
):
    generation = _generate_codes(logged_client)
    code = generation[0]

    reloaded = logged_client.get(reverse("mfa_backup_codes"))

    assert reloaded.status_code == 200
    assert reloaded.context["codes"] is None
    assert reloaded.context["has_codes"] is True
    assert code not in reloaded.content.decode()


# --- Fallback verification (mfa_verify) ---


def test_verify_backup_mode_renders_backup_form(client, user, confirmed_device):
    _login(client, user)

    response = client.get(reverse("mfa_verify") + "?backup=1")

    assert response.status_code == 200
    assert response.context["show_backup"] is True
    assert "backup_code" in response.content.decode()


def test_verify_wrong_totp_offers_backup_form(client, user, confirmed_device):
    _login(client, user)

    response = client.post(
        reverse("mfa_verify"), data={"token": _invalid_totp(confirmed_device)}
    )

    assert response.status_code == 200
    assert response.context["form"].errors
    assert response.context["show_backup"] is True
    assert "backup_code" in response.content.decode()


def test_verify_with_backup_code_marks_session_verified(client, user, confirmed_device):
    _login(client, user)
    code = _generate_codes(client)[0]

    response = client.post(reverse("mfa_verify"), data={"backup_code": code})

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")

    device = StaticDevice.objects.get(user=user)
    assert client.session[DEVICE_ID_SESSION_KEY] == device.persistent_id

    final = client.get(response["Location"])
    assert final.wsgi_request.user.is_verified() is True


def test_backup_code_is_single_use(client, user, confirmed_device):
    _login(client, user)
    code = _generate_codes(client)[0]

    first = client.post(reverse("mfa_verify"), data={"backup_code": code})
    assert first.status_code == 302
    assert DEVICE_ID_SESSION_KEY in client.session

    client.post(reverse("logout"))
    _login(client, user)

    reuse = client.post(reverse("mfa_verify"), data={"backup_code": code})

    assert reuse.status_code == 200
    assert reuse.context["backup_form"].errors
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_verify_with_wrong_backup_code_rejected(client, user, confirmed_device):
    _login(client, user)
    _generate_codes(client)

    response = client.post(
        reverse("mfa_verify"), data={"backup_code": "zzzzzzzzzz"}
    )

    assert response.status_code == 200
    assert response.context["backup_form"].errors
    assert DEVICE_ID_SESSION_KEY not in client.session


# --- Login gate and profile entry point ---


def test_login_gate_ignores_a_static_device_only(client, user, static_device):
    # Decision: backup codes are a fallback, not an independent factor. A
    # StaticDevice without a confirmed TOTPDevice must NOT force the second step.
    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")
    assert DEVICE_ID_SESSION_KEY not in client.session

    # The second step has nothing to verify either.
    assert client.get(reverse("mfa_verify"))["Location"] == reverse("perfil_personal")


def test_profile_shows_backup_codes_link(logged_client):
    response = logged_client.get(reverse("perfil_personal"))

    assert response.status_code == 200
    assert reverse("mfa_backup_codes") in response.content.decode()
