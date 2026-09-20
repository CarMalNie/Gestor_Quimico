"""Password change flow tests (native Django auth views).

Covers: login enforcement on both routes, authenticated rendering of the form,
wrong old password rejection, weak new password rejection by
AUTH_PASSWORD_VALIDATORS, the successful change (redirect to the done view,
new password authenticates, old one stops working) and the session surviving
the change thanks to ``update_session_auth_hash``.
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

pytestmark = pytest.mark.django_db

OLD_PASSWORD = "ClaveVieja123"
NEW_PASSWORD = "ClaveNueva456"


@pytest.fixture
def user():
    return User.objects.create_user(
        username="quimico", password=OLD_PASSWORD, email="quimico@correo.com"
    )


@pytest.fixture
def logged_client(client, user):
    client.force_login(user)
    return client


def _post_change(client, old_password, new_password):
    return client.post(
        reverse("password_change"),
        data={
            "old_password": old_password,
            "new_password1": new_password,
            "new_password2": new_password,
        },
    )


# --- Login enforcement ---


@pytest.mark.parametrize("name", ["password_change", "password_change_done"])
def test_anonymous_user_is_redirected_to_login(client, name):
    response = client.get(reverse(name))

    assert response.status_code == 302
    assert reverse("login") in response["Location"]


# --- Authenticated form ---


def test_authenticated_get_renders_the_form(logged_client):
    response = logged_client.get(reverse("password_change"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "old_password" in content
    assert "new_password1" in content
    assert "new_password2" in content


# --- Rejections keep the old password ---


def test_wrong_old_password_is_rejected(logged_client, user):
    response = _post_change(logged_client, "clave-incorrecta", NEW_PASSWORD)

    assert response.status_code == 200
    assert response.context["form"].errors

    user.refresh_from_db()
    assert user.check_password(OLD_PASSWORD)
    assert not user.check_password(NEW_PASSWORD)


def test_weak_new_password_is_rejected(logged_client, user):
    # "password" is rejected by CommonPasswordValidator.
    response = _post_change(logged_client, OLD_PASSWORD, "password")

    assert response.status_code == 200
    assert response.context["form"].errors

    user.refresh_from_db()
    assert user.check_password(OLD_PASSWORD)


# --- Successful change ---


def test_successful_change_redirects_to_done_and_rotates_password(logged_client, user):
    response = _post_change(logged_client, OLD_PASSWORD, NEW_PASSWORD)

    assert response.status_code == 302
    assert response["Location"] == reverse("password_change_done")

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(OLD_PASSWORD)


def test_session_survives_the_password_change(logged_client):
    _post_change(logged_client, OLD_PASSWORD, NEW_PASSWORD)

    # No re-login required: the profile page still resolves for this client.
    assert logged_client.get(reverse("perfil_personal")).status_code == 200


def test_profile_page_shows_change_password_link(logged_client):
    response = logged_client.get(reverse("perfil_personal"))

    assert response.status_code == 200
    assert reverse("password_change") in response.content.decode()


def test_new_password_authenticates_while_old_one_does_not(client, user):
    client.force_login(user)
    _post_change(client, OLD_PASSWORD, NEW_PASSWORD)
    client.logout()

    # The new password authenticates: the login redirects to the landing page.
    # HTTP POST is used instead of client.login() because the django-axes
    # backend requires a request object and rejects the direct helper call.
    new_login = client.post(
        reverse("login"),
        data={"username": user.username, "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 302
    assert new_login["Location"] == reverse("perfil_personal")

    client.logout()

    # The old password no longer authenticates: the form is redisplayed.
    old_login = client.post(
        reverse("login"),
        data={"username": user.username, "password": OLD_PASSWORD},
    )
    assert old_login.status_code == 200
    assert "_auth_user_id" not in client.session
