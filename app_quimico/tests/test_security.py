"""Security tests: response headers and login rate limiting (django-axes)."""

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def login_user():
    return User.objects.create_user(
        username="victim", password="pass12345", email="victim@correo.com"
    )


def _failed_login(client, username):
    return client.post(reverse("login"), data={"username": username, "password": "wrong-pass"})


def test_security_headers_present(client):
    response = client.get(reverse("home"))
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["X-Frame-Options"] == "DENY"


def test_login_locks_out_after_failure_limit(client, login_user):
    for _ in range(5):
        _failed_login(client, "victim")

    response = _failed_login(client, "victim")
    # django-axes default lockout response uses 429 (Too Many Requests).
    assert response.status_code == 429
    # The correct password must also be rejected while locked out.
    locked = client.post(reverse("login"), data={
        "username": "victim", "password": "pass12345",
    })
    assert locked.status_code == 429


def test_failure_limit_left_after_reset(client, login_user):
    for _ in range(5):
        _failed_login(client, "victim")
    AccessAttempt.objects.all().delete()

    response = client.post(reverse("login"), data={
        "username": "victim", "password": "pass12345",
    })
    assert response.status_code == 302  # successful login redirects
