"""Force-MFA policy tests: the Administradores group must enrol MFA after login.

Operator decision B: two-step authentication is mandatory ONLY for the
'Administradores' group. An Administrador without a confirmed TOTP device is
redirected to 'mfa_setup' right after password login; everyone else keeps the
current voluntary behaviour.

Login goes through HTTP POST to the login route because django-axes rejects the
direct ``client.login()`` helper (same pattern as ``test_mfa_totp.py``).
"""

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
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
