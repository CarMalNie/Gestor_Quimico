"""Password recovery flow tests (native Django auth views + email backend).

Covers: reset request without user enumeration, reset done page, full token
confirmation flow (new password works, old one stops working), invalid and
expired tokens, password validators on the confirm form, the forgot-password
link on the login page, and the interoperability with the django-axes login
lockout (a locked account must still be able to request a reset).
"""

import re

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

pytestmark = pytest.mark.django_db

OLD_PASSWORD = "ClaveVieja123"
NEW_PASSWORD = "ClaveNueva456"
RESET_LINK_RE = re.compile(r"(?P<path>/accounts/reset/[^\s]+)")


@pytest.fixture(autouse=True)
def _email_backend(settings):
    """Never send real email: keep every message in the in-memory outbox."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "no-reply@gestorquimico.local"
    mail.outbox = []
    yield
    mail.outbox = []


@pytest.fixture
def user():
    return User.objects.create_user(
        username="quimico", password=OLD_PASSWORD, email="quimico@correo.com"
    )


def _request_reset(client, email):
    return client.post(reverse("password_reset"), data={"email": email})


def _reset_link_path():
    """Extracts the reset link path from the only message in the outbox."""
    body = mail.outbox[0].body
    match = RESET_LINK_RE.search(body)
    assert match, f"reset link not found in email body:\n{body}"
    return match.group("path")


def _split_uid_and_token(path):
    _, _, uidb64, token = path.strip("/").split("/")
    return uidb64, token


# --- Reset request: no user enumeration ---


def test_reset_request_form_renders(client):
    response = client.get(reverse("password_reset"))
    assert response.status_code == 200
    assert "correo" in response.content.decode().lower()


def test_reset_request_same_response_for_known_and_unknown_email(client, user):
    known = _request_reset(client, user.email)
    unknown = _request_reset(client, "no-existe@correo.com")

    assert known.status_code == unknown.status_code == 302
    assert known["Location"] == unknown["Location"]

    # Only the existing address produces a message: no enumeration.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]


def test_password_reset_done_returns_200(client):
    response = client.get(reverse("password_reset_done"))
    assert response.status_code == 200


# --- Full token confirmation flow ---


def test_full_reset_flow_sets_new_password(client, user):
    _request_reset(client, user.email)
    assert len(mail.outbox) == 1

    # Following the emailed link redirects to the internal set-password URL.
    response = client.get(_reset_link_path())
    assert response.status_code == 302
    set_password_url = response["Location"]

    response = client.post(
        set_password_url,
        data={"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("password_reset_complete")

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(OLD_PASSWORD)

    complete = client.get(response["Location"])
    assert complete.status_code == 200


def test_weak_password_is_rejected_by_validators(client, user):
    _request_reset(client, user.email)
    set_password_url = client.get(_reset_link_path())["Location"]

    response = client.post(
        set_password_url,
        data={"new_password1": "12345", "new_password2": "12345"},
    )

    assert response.status_code == 200
    assert response.context["form"].errors

    user.refresh_from_db()
    assert user.check_password(OLD_PASSWORD)


# --- Invalid and expired tokens ---


@pytest.mark.parametrize("tipo", ["invalido", "expirado"])
def test_invalid_or_expired_token_shows_invalid_link(client, user, settings, tipo):
    if tipo == "invalido":
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = "token-invalido"
    else:
        settings.PASSWORD_RESET_TIMEOUT = -1
        _request_reset(client, user.email)
        uidb64, token = _split_uid_and_token(_reset_link_path())

    response = client.get(
        reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token})
    )

    assert response.status_code == 200
    assert "no es válido" in response.content.decode().lower()


def test_valid_token_renders_password_form(client, user):
    _request_reset(client, user.email)
    uidb64, token = _split_uid_and_token(_reset_link_path())

    response = client.get(
        reverse("password_reset_confirm", kwargs={"uidb64": uidb64, "token": token}),
        follow=True,
    )

    assert response.status_code == 200
    assert "new_password1" in response.content.decode()
    assert "no es válido" not in response.content.decode().lower()


# --- Login page integration ---


def test_login_page_still_renders_and_shows_forgot_password_link(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert reverse("password_reset") in response.content.decode()


# --- django-axes interoperability ---


def test_axes_lockout_does_not_block_reset_request(client, user):
    for _ in range(5):
        client.post(
            reverse("login"),
            data={"username": user.username, "password": "clave-incorrecta"},
        )
    assert AccessAttempt.objects.filter(username=user.username).exists()

    response = _request_reset(client, user.email)

    assert response.status_code == 302
    assert len(mail.outbox) == 1
