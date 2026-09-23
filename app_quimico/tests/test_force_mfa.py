"""Force-MFA policy tests: the Administradores group must enrol MFA after login.

Operator decision B: two-step authentication is mandatory ONLY for the
'Administradores' group. An Administrador without a confirmed TOTP device is
redirected to 'mfa_setup' right after password login; everyone else keeps the
current voluntary behaviour.

The second section covers the session-wide enforcement (ForceMFAAdminMiddleware):
once logged in, an Administrador without MFA cannot navigate anywhere except
'mfa_setup', 'logout' and the static/media assets. Superusers OUTSIDE the group
are unaffected (the policy is group-based, not is_staff/is_superuser based).

Login goes through HTTP POST to the login route because django-axes rejects the
direct ``client.login()`` helper (same pattern as ``test_mfa_totp.py``).
"""

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
ADMIN_GROUP = "Administradores"
REGULAR_GROUP = "Quimicos"


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


def _make_user(username, group_name=None):
    user = User.objects.create_user(
        username=username, password=PASSWORD, email=f"{username}@correo.com"
    )
    if group_name is not None:
        user.groups.add(Group.objects.get(name=group_name))
    return user


def _login(client, user, follow=False):
    return client.post(
        reverse("login"),
        data={"username": user.username, "password": PASSWORD},
        follow=follow,
    )


def _token(device, drift=0):
    """Current token for ``device``, generated from its own secret.

    Mirrors ``test_mfa_totp.py``: ``django_otp.test_utils`` is avoided because it
    imports ``freezegun``, which is not an installed dependency.
    """
    value = totp(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift + drift,
    )
    return f"{value:06d}"


# --- Administradores: mandatory MFA ---


def test_admin_without_device_is_redirected_to_setup(client):
    user = _make_user("admin_sin_mfa", ADMIN_GROUP)

    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("mfa_setup")
    assert DEVICE_ID_SESSION_KEY not in client.session


def test_admin_without_device_sees_warning_message(client):
    user = _make_user("admin_sin_mfa", ADMIN_GROUP)

    response = _login(client, user, follow=True)

    assert response.redirect_chain[-1][0] == reverse("mfa_setup")
    assert "requiere autenticación en dos pasos" in response.content.decode()


def test_admin_with_unconfirmed_device_is_redirected_to_setup(client):
    # A stale, never-confirmed device does not grant a pass: the gate keys off
    # ``confirmed=True`` only, so the admin still has to finish enrolment.
    user = _make_user("admin_parcial", ADMIN_GROUP)
    TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=False)

    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("mfa_setup")


def test_admin_with_confirmed_device_keeps_second_factor_flow(client):
    user = _make_user("admin_con_mfa", ADMIN_GROUP)
    TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=True)

    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("mfa_verify")
    # Password login alone does not verify the session.
    assert DEVICE_ID_SESSION_KEY not in client.session


# --- Everyone else: voluntary MFA, normal login ---


def test_regular_group_user_without_device_gets_normal_success(client):
    user = _make_user("quimico_sin_mfa", REGULAR_GROUP)

    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")

    landing = client.get(response["Location"])
    assert "Has iniciado sesión con éxito" in landing.content.decode()


def test_ungrouped_user_without_device_gets_normal_success(client):
    user = _make_user("sin_grupo")

    response = _login(client, user)

    assert response.status_code == 302
    assert response["Location"] == reverse("perfil_personal")


# --- Session-wide enforcement (ForceMFAAdminMiddleware) ---


def test_admin_without_mfa_is_blocked_outside_setup(client):
    user = _make_user("nav_admin", ADMIN_GROUP)
    _login(client, user)

    response = client.get(reverse("perfil_personal"))

    assert response.status_code == 302
    assert response["Location"] == reverse("mfa_setup")


def test_admin_block_emits_middleware_warning(client):
    user = _make_user("nav_admin_warn", ADMIN_GROUP)
    # follow=True consumes the login-time warning so the only warning left in
    # the session is the one the middleware adds on the blocked navigation.
    _login(client, user, follow=True)

    response = client.get(reverse("perfil_personal"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("mfa_setup")
    assert (
        "requiere configurar la verificación en dos pasos antes de continuar"
        in response.content.decode()
    )


def test_admin_without_mfa_can_open_setup_without_loop(client):
    user = _make_user("nav_admin_loop", ADMIN_GROUP)
    _login(client, user)

    response = client.get(reverse("mfa_setup"))

    assert response.status_code == 200


def test_admin_without_mfa_can_logout(client):
    user = _make_user("nav_admin_logout", ADMIN_GROUP)
    _login(client, user)

    # Logout is @require_POST in this project, so the exemption is exercised
    # with a POST (a GET would answer 405 before the middleware matters).
    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert response["Location"] != reverse("mfa_setup")


def test_admin_browses_freely_after_enrolment(client):
    user = _make_user("nav_admin_enrol", ADMIN_GROUP)
    _login(client, user)

    client.get(reverse("mfa_setup"))
    device = TOTPDevice.objects.get(user=user)
    enrolled = client.post(reverse("mfa_setup"), data={"token": _token(device)})
    assert enrolled.status_code == 302

    response = client.get(reverse("perfil_personal"))

    assert response.status_code == 200


def test_admin_with_confirmed_device_browses_without_second_factor(client):
    # Guard (f) of the middleware: an existing confirmed device lifts the
    # navigation block on its own. The second-factor prompt stays the login
    # flow's job (mfa_verify), which is what this unverified session proves.
    user = _make_user("nav_admin_confirmed", ADMIN_GROUP)
    TOTPDevice.objects.create(user=user, name="Authenticator", confirmed=True)
    _login(client, user)

    assert DEVICE_ID_SESSION_KEY not in client.session

    response = client.get(reverse("perfil_personal"))

    assert response.status_code == 200


def test_regular_user_browses_profile_without_mfa(client):
    user = _make_user("nav_regular", REGULAR_GROUP)
    _login(client, user)

    response = client.get(reverse("perfil_personal"))

    assert response.status_code == 200


def test_superuser_without_admin_group_browses_profile(client):
    # Group-based boundary: is_superuser alone does not trigger the policy.
    user = User.objects.create_superuser(
        username="nav_root", password=PASSWORD, email="root@correo.com"
    )
    _login(client, user)

    response = client.get(reverse("perfil_personal"))

    assert response.status_code == 200


def test_admin_setup_hides_the_profile_link(client):
    user = _make_user("nav_admin_link", ADMIN_GROUP)
    _login(client, user)

    response = client.get(reverse("mfa_setup"))

    assert response.status_code == 200
    assert "Volver a mi perfil" not in response.content.decode()


def test_regular_setup_keeps_the_profile_link(client):
    user = _make_user("nav_regular_link", REGULAR_GROUP)
    client.force_login(user)

    response = client.get(reverse("mfa_setup"))

    assert "Volver a mi perfil" in response.content.decode()
