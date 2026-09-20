"""Brevo transactional email backend over the HTTP API.

Sends through ``POST https://api.brevo.com/v3/smtp/email`` with an ``api-key``
header instead of opening an SMTP connection. PythonAnywhere free web apps
cannot reach outbound SMTP (the proxy only publishes whitelisted HTTP(S)
endpoints, and ``api.brevo.com`` is on that list), so this backend is the
production delivery path there while SMTP stays valid for local development.

Failures raise ``smtplib.SMTPException``: Django's
``PasswordResetForm.send_mail`` catches that exception and logs
"Failed to send password reset email", so a rejected request never turns into
a 500 for the user and the failure stays visible in the server error log.

Attachments are out of scope (password recovery emails have none): a warning is
logged and the body is sent on its own.
"""

import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.utils import parseaddr

from decouple import config
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'
BREVO_TIMEOUT_SECONDS = 10


def _parse_address(address):
    """Split ``"Nombre <user@host>"`` into Brevo's ``{name, email}`` form."""
    name, email = parseaddr(address or '')
    parsed = {'name': name, 'email': email}
    return {key: value for key, value in parsed.items() if value}


class BrevoApiEmailBackend(BaseEmailBackend):
    """Django email backend that posts each message to the Brevo HTTP API."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = config('EMAIL_API_KEY', default='')
        if not self.api_key.strip():
            raise ImproperlyConfigured(
                'BrevoApiEmailBackend requires EMAIL_API_KEY. Set the Brevo API '
                'key (panel: SMTP & API -> API Keys) in the environment, or pick '
                'another EMAIL_BACKEND explicitly.'
            )

    def _send(self, message):
        """Build the Brevo payload for ``message`` (no HTTP call)."""
        if message.attachments:
            logger.warning(
                'BrevoApiEmailBackend does not support attachments: dropped %s '
                'attachment(s) from %r and sent the body only.',
                len(message.attachments),
                message.subject,
            )

        content_key = (
            'htmlContent' if message.content_subtype == 'html' else 'textContent'
        )
        payload = {
            'sender': _parse_address(message.from_email),
            'to': [_parse_address(address) for address in message.to],
            'cc': [_parse_address(address) for address in message.cc],
            'bcc': [_parse_address(address) for address in message.bcc],
            'subject': message.subject,
            content_key: message.body,
        }
        # Brevo rejects null fields and empty recipient lists: keep only the
        # values the message actually produced.
        return {key: value for key, value in payload.items() if value}

    def _post(self, payload):
        """POST one payload to Brevo; raise ``SMTPException`` on failure."""
        request = urllib.request.Request(
            BREVO_API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'api-key': self.api_key},
            method='POST',
        )
        try:
            with urllib.request.urlopen(
                request, timeout=BREVO_TIMEOUT_SECONDS
            ) as response:
                status = response.status
                body = response.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as error:
            detail = error.read().decode('utf-8', errors='replace')
            raise smtplib.SMTPException(
                f'Brevo API rejected the message (HTTP {error.code}): {detail}'
            ) from error
        except OSError as error:
            # Covers URLError (DNS/refused/TLS) and socket timeouts.
            reason = getattr(error, 'reason', error)
            raise smtplib.SMTPException(
                f'Brevo API request failed: {reason}'
            ) from error

        if not 200 <= status < 300:
            raise smtplib.SMTPException(
                f'Brevo API rejected the message (HTTP {status}): {body}'
            )

    def send_messages(self, email_messages):
        """Send each message once; return how many were accepted by Brevo."""
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            try:
                self._post(self._send(message))
            except smtplib.SMTPException as error:
                if not self.fail_silently:
                    raise
                logger.warning('Brevo API send failed silently: %s', error)
                continue
            sent += 1
        return sent
