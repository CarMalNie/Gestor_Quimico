"""TOTP MFA tests (django-otp): enrolment, login second step and admin.

Login in tests goes through HTTP POST to the login route because django-axes
rejects the direct ``client.login()`` helper (same pattern as
``test_password_change.py`` / ``test_password_reset.py``).

Tokens are generated with ``django_otp.oath`` from the device's own key:
``django_otp.test_utils`` is not used because it imports ``freezegun``, which
is not an installed dependency.
"""

from urllib.parse import parse_qs, quote, urlencode, urlsplit

import pytest
from axes.models import AccessAttempt
from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
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


def _invalid_token(device):
    """Deterministic code that is outside the device tolerance window."""
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


def _login(client, user, next_url=None):
    """HTTP-POST login. ``next_url`` mirrors a ``?next=`` on the login request."""
    url = reverse("login")
    if next_url is not None:
        url = f"{url}?{urlencode({'next': next_url})}"
    return client.post(url, data={"username": user.username, "password": PASSWORD})


# --- Enrolment (mfa_setup) ---


def test_setup_requires_login(client):
    response = client.get(reverse("mfa_setup"))

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_setup_get_creates_unconfirmed_device_and_renders_qr(logged_client, user):
    response = logged_client.get(reverse("mfa_setup"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "<svg" in content  # QR rendered as inline SVG (no Pillow needed)
    assert "otpauth://totp/" in content

    device = TOTPDevice.objects.get(user=user)
    assert device.confirmed is False


def test_setup_get_reuses_the_pending_device(logged_client, user):
    logged_client.get(reverse("mfa_setup"))
    logged_client.get(reverse("mfa_setup"))

    assert TOTPDevice.objects.filter(user=user, confirmed=False).count() == 1


def test_setup_confirm_with_valid_token_activates_device(logged_client, user):
    logged_client.get(reverse("mfa_setup"))
    device = TOTPDevice.objects.get(user=user)

    response = logged_client.post(reverse("mfa_setup"), data={"token": _token(device)})

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")

    device.refresh_from_db()
    assert device.confirmed is True


def test_setup_wrong_token_does_not_activate_device(logged_client, user):
    logged_client.get(reverse("mfa_setup"))
    device = TOTPDevice.objects.get(user=user)

    response = logged_client.post(
        reverse("mfa_setup"), data={"token": _invalid_token(device)}
    )

    assert response.status_code == 200
    assert response.context["form"].errors

    device.refresh_from_db()
    assert device.confirmed is False


def test_setup_shows_enrolled_status_for_confirmed_device(
    logged_client, confirmed_device
):
    response = logged_client.get(reverse("mfa_setup"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "ya está activada" in content
    # No new pending device / enrolment QR is offered.
    assert "otpauth://" not in content


def test_profile_shows_mfa_setup_link(logged_client):
    response = logged_client.get(reverse("perfil_personal"))

    assert response.status_code == 200
    assert reverse("mfa_setup") in response.content.decode()


# --- Login second step (mfa_verify) ---


def test_login_without_device_goes_straight_to_profile(client, user):
    # Regression: unchanged post-login destination (LOGIN_REDIRECT_URL).
    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_login_without_device_honours_next(client, user):
    # Regression guard: without a device, LoginView still honours ?next= as
    # before the MFA second step was introduced.
    next_value = reverse("password_change")

    response = _login(client, user, next_url=next_value)

    assert response.status_code == 302
    assert response["Location"] == next_value
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_login_with_confirmed_device_leaves_session_unverified(
    client, user, confirmed_device
):
    _login(client, user)

    assert "_auth_user_id" in client.session
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_login_with_confirmed_device_redirects_to_mfa_verify(
    client, user, confirmed_device
):
    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("mfa_verify")

    # The session is authenticated but not yet OTP-verified...
    assert "_auth_user_id" in client.session
    assert DEVICE_ID_SESSION_KEY not in client.session

    # ...and the welcome message is deliberately withheld until the token is
    # verified, so the second step cannot be skipped by reading the landing page.
    pending = client.get(reverse("mfa_verify"))
    assert "Has iniciado sesión con éxito" not in pending.content.decode()


def test_login_with_confirmed_device_forwards_next_to_mfa_verify(
    client, user, confirmed_device
):
    # A next target carrying its own query string: it MUST be quoted when
    # appended to the mfa_verify URL, otherwise the second step would read a
    # truncated destination.
    next_value = reverse("password_change") + "?origen=login"

    response = _login(client, user, next_url=next_value)

    assert response.status_code == 302
    assert (
        response["Location"]
        == reverse("mfa_verify") + "?next=" + quote(next_value)
    )
    # Quoting is not cosmetic: the raw value survives the round trip.
    forwarded = parse_qs(urlsplit(response["Location"]).query)["next"]
    assert forwarded == [next_value]

    # The session is authenticated but still pending the token.
    assert "_auth_user_id" in client.session
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_verify_requires_login(client):
    response = client.get(reverse("mfa_verify"))

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_verify_get_renders_token_form(client, user, confirmed_device):
    _login(client, user)

    response = client.get(reverse("mfa_verify"))

    assert response.status_code == 200
    assert "token" in response.content.decode()


def test_verify_without_confirmed_device_redirects(logged_client):
    response = logged_client.get(reverse("mfa_verify"))

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")


def test_verify_wrong_token_keeps_session_unverified(client, user, confirmed_device):
    _login(client, user)

    response = client.post(
        reverse("mfa_verify"), data={"token": _invalid_token(confirmed_device)}
    )

    assert response.status_code == 200
    assert response.context["form"].errors
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_verify_valid_token_marks_session_verified(client, user, confirmed_device):
    _login(client, user)

    response = client.post(
        reverse("mfa_verify"), data={"token": _token(confirmed_device)}
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")
    assert client.session[DEVICE_ID_SESSION_KEY] == confirmed_device.persistent_id

    final = client.get(response["Location"])
    assert final.wsgi_request.user.is_verified() is True


def test_verify_with_valid_token_honours_next(client, user, confirmed_device):
    next_value = reverse("password_change")
    _login(client, user)

    response = client.post(
        reverse("mfa_verify"),
        data={"token": _token(confirmed_device), "next": next_value},
    )

    assert response.status_code == 302
    assert response["Location"] == next_value
    # Not the default landing page: the forwarded destination wins.
    assert response["Location"] != reverse("perfil_personal")
    assert client.session[DEVICE_ID_SESSION_KEY] == confirmed_device.persistent_id

    final = client.get(response["Location"])
    assert final.status_code == 200


# --- Session lifecycle, axes interplay and admin ---


def test_mfa_route_does_not_bypass_axes_lockout(client, user, confirmed_device):
    """A user locked out by axes cannot skip password auth via the MFA route."""
    for _ in range(5):
        client.post(
            reverse("login"),
            data={"username": user.username, "password": "clave-incorrecta"},
        )

    # axes keeps rejecting even the correct password while locked out...
    locked = _login(client, user)
    assert locked.status_code == 429

    # ...and the anonymous client cannot reach the second MFA step directly.
    response = client.get(reverse("mfa_verify"))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


def test_logout_works_with_otp_middleware(logged_client):
    response = logged_client.post(reverse("logout"))

    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert "_auth_user_id" not in logged_client.session


def test_totp_device_admin_is_registered(admin_client):
    assert TOTPDevice in admin.site._registry

    response = admin_client.get(reverse("admin:otp_totp_totpdevice_changelist"))

    assert response.status_code == 200
