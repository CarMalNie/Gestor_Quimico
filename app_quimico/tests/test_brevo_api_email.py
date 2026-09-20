"""Brevo HTTP API email backend tests.

The HTTP layer is patched (``urllib.request.urlopen``) so no request ever
leaves the test process: URL, headers and JSON payload are asserted directly
and stand in for a live Brevo call. The API key used here is an obvious
placeholder, never a real credential.
"""

import io
import json
import logging
import smtplib
import urllib.error
from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, send_mail
from django.test import override_settings

from app_quimico import brevo_api_backend
from app_quimico.brevo_api_backend import BREVO_API_URL, BrevoApiEmailBackend

API_KEY = "xkeysib-test"
FROM_EMAIL = "Gestor Químico <no-reply@gestorquimico.local>"
URLOPEN = "app_quimico.brevo_api_backend.urllib.request.urlopen"


class FakeResponse:
    """Minimal stand-in for the context manager returned by ``urlopen``."""

    def __init__(self, status=201, payload=None):
        self.status = status
        body = {"messageId": "<2026092000@brevo>"} if payload is None else payload
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _http_error(status, payload):
    return urllib.error.HTTPError(
        BREVO_API_URL,
        status,
        "error",
        {},
        io.BytesIO(json.dumps(payload).encode("utf-8")),
    )


@pytest.fixture
def api_key(monkeypatch):
    """Feeds a fake EMAIL_API_KEY to the backend's ``config`` lookup."""
    monkeypatch.setattr(
        brevo_api_backend,
        "config",
        lambda key, default="", **kwargs: (
            API_KEY if key == "EMAIL_API_KEY" else default
        ),
    )


def _message(body="Restablece tu contraseña.", subject="Recuperación de contraseña"):
    return EmailMessage(
        subject=subject,
        body=body,
        from_email=FROM_EMAIL,
        to=["quimico@correo.com", "Jefa Laboratorio <jefa@correo.com>"],
        cc=["copia@correo.com"],
        bcc=["oculto@correo.com"],
    )


def _request_and_payload(mocked_urlopen):
    request = mocked_urlopen.call_args.args[0]
    return request, json.loads(request.data.decode("utf-8"))


# --- Configuration ---


@pytest.mark.parametrize("value", ["", "   "])
def test_missing_or_blank_api_key_raises_improperly_configured(
    monkeypatch, value
):
    monkeypatch.setattr(
        brevo_api_backend, "config", lambda key, default="", **kwargs: default
    )

    with pytest.raises(ImproperlyConfigured) as excinfo:
        BrevoApiEmailBackend()

    assert "EMAIL_API_KEY" in str(excinfo.value)


def test_configured_backend_keeps_the_key(api_key):
    assert BrevoApiEmailBackend().api_key == API_KEY


# --- Success path ---


@pytest.mark.parametrize("status", [200, 201, 204])
def test_2xx_counts_the_message_as_sent(api_key, status):
    with patch(URLOPEN, return_value=FakeResponse(status)) as mocked_urlopen:
        sent = BrevoApiEmailBackend().send_messages([_message()])

    assert sent == 1
    assert mocked_urlopen.call_count == 1


def test_success_posts_url_headers_and_expected_payload(api_key):
    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        BrevoApiEmailBackend().send_messages([_message()])

    request, payload = _request_and_payload(mocked_urlopen)

    assert request.full_url == BREVO_API_URL
    assert request.method == "POST"
    assert request.headers["Api-key"] == API_KEY
    assert request.headers["Content-type"] == "application/json"
    assert mocked_urlopen.call_args.kwargs["timeout"] == 10

    # "Nombre <addr>" is split into name + email; a plain address has no name.
    assert payload["sender"] == {
        "name": "Gestor Químico",
        "email": "no-reply@gestorquimico.local",
    }
    assert payload["to"] == [
        {"email": "quimico@correo.com"},
        {"name": "Jefa Laboratorio", "email": "jefa@correo.com"},
    ]
    assert payload["cc"] == [{"email": "copia@correo.com"}]
    assert payload["bcc"] == [{"email": "oculto@correo.com"}]
    assert payload["subject"] == "Recuperación de contraseña"
    assert payload["textContent"] == "Restablece tu contraseña."
    assert "htmlContent" not in payload


def test_html_message_is_sent_as_html_content(api_key):
    message = _message(body="<p>Restablece tu contraseña.</p>")
    message.content_subtype = "html"

    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        BrevoApiEmailBackend().send_messages([message])

    _, payload = _request_and_payload(mocked_urlopen)

    assert payload["htmlContent"] == "<p>Restablece tu contraseña.</p>"
    assert "textContent" not in payload


def test_empty_recipient_lists_are_omitted_from_the_payload(api_key):
    message = EmailMessage(
        subject="Recuperación de contraseña",
        body="Restablece tu contraseña.",
        from_email="no-reply@gestorquimico.local",
        to=["quimico@correo.com"],
    )

    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        BrevoApiEmailBackend().send_messages([message])

    _, payload = _request_and_payload(mocked_urlopen)

    assert payload["sender"] == {"email": "no-reply@gestorquimico.local"}
    assert payload["to"] == [{"email": "quimico@correo.com"}]
    assert "cc" not in payload
    assert "bcc" not in payload


def test_multiple_messages_are_posted_once_each(api_key):
    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        sent = BrevoApiEmailBackend().send_messages(
            [_message(), _message(subject="Otra recuperación")]
        )

    assert sent == 2
    assert mocked_urlopen.call_count == 2


def test_no_messages_sends_nothing(api_key):
    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        sent = BrevoApiEmailBackend().send_messages([])

    assert sent == 0
    assert mocked_urlopen.call_count == 0


# --- Failure paths ---


def test_non_2xx_raises_smtp_exception_with_the_brevo_error(api_key):
    error = _http_error(
        400, {"code": "invalid_parameter", "message": "sender is required"}
    )

    with patch(URLOPEN, side_effect=error):
        with pytest.raises(smtplib.SMTPException) as excinfo:
            BrevoApiEmailBackend().send_messages([_message()])

    # Django's PasswordResetForm catches SMTPException: the Brevo text must
    # reach that handler so the failure is logged instead of a 500.
    assert "sender is required" in str(excinfo.value)
    assert "400" in str(excinfo.value)


def test_network_error_raises_smtp_exception(api_key):
    with patch(URLOPEN, side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(smtplib.SMTPException):
            BrevoApiEmailBackend().send_messages([_message()])


def test_fail_silently_returns_zero_instead_of_raising(api_key):
    error = _http_error(401, {"message": "Key not found"})

    with patch(URLOPEN, side_effect=error):
        sent = BrevoApiEmailBackend(fail_silently=True).send_messages(
            [_message(), _message()]
        )

    assert sent == 0


def test_attachments_are_warned_about_and_text_is_still_sent(api_key, caplog):
    message = _message()
    message.attach("reporte.txt", "contenido", "text/plain")

    with caplog.at_level(logging.WARNING, logger="app_quimico.brevo_api_backend"):
        with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
            sent = BrevoApiEmailBackend().send_messages([message])

    assert sent == 1
    assert "attachment" in caplog.text.lower()
    _, payload = _request_and_payload(mocked_urlopen)
    assert payload["textContent"] == "Restablece tu contraseña."


# --- Drop-in replacement for django.core.mail ---


@override_settings(
    EMAIL_BACKEND="app_quimico.brevo_api_backend.BrevoApiEmailBackend",
    DEFAULT_FROM_EMAIL="Gestor Químico <no-reply@gestorquimico.local>",
)
def test_send_mail_goes_through_the_brevo_backend(api_key):
    with patch(URLOPEN, return_value=FakeResponse(201)) as mocked_urlopen:
        send_mail(
            "Recuperación de contraseña",
            "Restablece tu contraseña.",
            None,
            ["quimico@correo.com"],
        )

    request, payload = _request_and_payload(mocked_urlopen)

    assert request.full_url == BREVO_API_URL
    assert payload["sender"] == {
        "name": "Gestor Químico",
        "email": "no-reply@gestorquimico.local",
    }
    assert payload["to"] == [{"email": "quimico@correo.com"}]
    assert payload["textContent"] == "Restablece tu contraseña."
