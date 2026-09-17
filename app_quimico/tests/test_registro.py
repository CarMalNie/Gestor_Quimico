"""Registration form tests (email uniqueness)."""

import pytest

from django.contrib.auth.models import User

from app_quimico.forms import RegistroForm

pytestmark = pytest.mark.django_db


# --- Registration email uniqueness ---


def test_registro_rechaza_email_duplicado():
    User.objects.create_user(
        username="existente", password="pass12345", email="test@correo.com"
    )
    form = RegistroForm(data={
        "username": "nuevo",
        "email": "TEST@correo.com",  # case-insensitive duplicate
        "first_name": "N",
        "last_name": "U",
        "password1": "pass12345",
        "password2": "pass12345",
    })
    assert not form.is_valid()
    assert "Ya existe una cuenta registrada" in str(form.errors)


def test_registro_acepta_email_nuevo():
    User.objects.create_user(
        username="existente", password="pass12345", email="test@correo.com"
    )
    form = RegistroForm(data={
        "username": "nuevo",
        "email": "otro@correo.com",
        "first_name": "N",
        "last_name": "U",
        "password1": "pass12345",
        "password2": "pass12345",
    })
    assert form.is_valid(), form.errors
