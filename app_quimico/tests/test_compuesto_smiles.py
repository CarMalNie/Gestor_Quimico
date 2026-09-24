"""Backend tests for the optional ``smiles`` field on ``CompuestoQuimico``.

Feature p2-2d-diagrams (Entrega 1), task T2: the model gains an optional
SMILES string used later to render a 2D structure diagram. The field must stay
fully optional (no diagram when empty) and must not change any existing
behavior, including ``__str__``.

These tests only cover the model + migration layer. Form validation and
persistence-through-views belong to T3 and are covered there.

Master tables (Industria) are seeded by migrations 0007/0008, so FK targets are
resolved with ``get_or_create`` — MySQL's case-insensitive unique collation
makes a plain ``create()`` collide with the seeded rows.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import TextField
from django.urls import reverse

from app_quimico.forms import CompuestoQuimicoForm
from app_quimico.models import (
    Aplicacion,
    CompuestoAplicacion,
    CompuestoQuimico,
    Industria,
)
from app_quimico.services import calcular_pm, registrar_elementos_compuesto

pytestmark = pytest.mark.django_db

MIGRATION_NAME = "0010_compuestoquimico_smiles"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SMILES_ETANOL = "CCO"


@pytest.fixture
def industria():
    return Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]


def _compuesto(industria, **kwargs):
    fields = {
        "nombre_compuesto": "Etanol",
        "formula_compuesto": "C2H6O",
        "id_industria": industria,
    }
    fields.update(kwargs)
    return CompuestoQuimico.objects.create(**fields)


# --- Field definition ---


def test_smiles_field_is_an_optional_textfield():
    field = CompuestoQuimico._meta.get_field("smiles")

    assert isinstance(field, TextField)
    assert field.blank is True
    assert field.null is True
    assert field.verbose_name == "Estructura SMILES"
    assert field.help_text == (
        "Notación SMILES opcional para mostrar la estructura 2D"
    )


def test_smiles_field_is_not_unique_or_indexed():
    field = CompuestoQuimico._meta.get_field("smiles")

    assert field.unique is False
    assert field.db_index is False


# --- Migration ---


def test_smiles_migration_file_exists_and_adds_the_field():
    candidates = sorted(MIGRATIONS_DIR.glob("0010_*.py"))

    assert len(candidates) == 1, candidates
    source = candidates[0].read_text(encoding="utf-8")
    assert "migrations.AddField" in source
    assert "name='smiles'" in source


def test_smiles_migration_is_applied():
    assert MigrationRecorder(connection).migration_qs.filter(
        app="app_quimico", name=MIGRATION_NAME
    ).exists()

    # The applied migration must have created the real column.
    with connection.cursor() as cursor:
        columns = {col.name for col in connection.introspection.get_table_description(
            cursor, CompuestoQuimico._meta.db_table
        )}
    assert "smiles" in columns


# --- Persistence ---


def test_compuesto_created_without_smiles_stores_none(industria):
    compuesto = _compuesto(industria)

    compuesto.refresh_from_db()
    assert compuesto.smiles is None


def test_compuesto_created_with_smiles_stores_the_value(industria):
    compuesto = _compuesto(industria, smiles=SMILES_ETANOL)

    compuesto.refresh_from_db()
    assert compuesto.smiles == SMILES_ETANOL


# --- Unchanged behavior ---


def test_str_is_unaffected_by_smiles(industria):
    sin_smiles = _compuesto(industria, formula_compuesto="CH4")
    con_smiles = _compuesto(industria, formula_compuesto="C2H6O", smiles=SMILES_ETANOL)

    assert str(sin_smiles) == "CH4 (Etanol)"
    assert str(con_smiles) == "C2H6O (Etanol)"
    assert SMILES_ETANOL not in str(con_smiles)


# ========================================================================= #
# T3 — Form validation + view persistence
# ========================================================================= #

PASSWORD = "ClaveSegura123"
FORMULA_ETANOL = "C2H6O"
ERROR_SMILES = "La notación SMILES no es válida"


def _form_data(**overrides):
    data = {
        "nombre_compuesto": "Etanol",
        "formula_compuesto": FORMULA_ETANOL,
        "smiles": SMILES_ETANOL,
    }
    data.update(overrides)
    return data


# --- Form field wiring ---


def test_form_exposes_the_optional_smiles_field():
    form = CompuestoQuimicoForm()

    assert "smiles" in form.fields
    assert form.fields["smiles"].required is False
    assert form.fields["smiles"].widget.attrs["placeholder"] == "Ej.: CCO (etanol)"


# --- clean_smiles ---


def test_form_accepts_valid_smiles():
    form = CompuestoQuimicoForm(data=_form_data(smiles="CCO"))

    assert form.is_valid(), form.errors
    assert form.cleaned_data["smiles"] == "CCO"


def test_form_strips_surrounding_whitespace():
    form = CompuestoQuimicoForm(data=_form_data(smiles="  CCO  "))

    assert form.is_valid(), form.errors
    assert form.cleaned_data["smiles"] == "CCO"


def test_form_accepts_empty_smiles_as_opt_out():
    """Empty input is a valid opt-out and normalizes to None (no diagram)."""
    form = CompuestoQuimicoForm(data=_form_data(smiles=""))

    assert form.is_valid(), form.errors
    assert form.cleaned_data["smiles"] is None


def test_form_rejects_invalid_smiles():
    # Unmatched ring-closure index: pysmiles raises while parsing.
    form = CompuestoQuimicoForm(data=_form_data(smiles="C1CC"))

    assert not form.is_valid()
    assert "smiles" in form.errors
    assert ERROR_SMILES in str(form.errors["smiles"])


def test_form_rejects_internal_whitespace_in_smiles():
    """'C C' parses in pysmiles as two unbonded atoms, so it is rejected
    explicitly to avoid silently accepting a malformed structure."""
    form = CompuestoQuimicoForm(data=_form_data(smiles="C C"))

    assert not form.is_valid()
    assert "smiles" in form.errors
    assert ERROR_SMILES in str(form.errors["smiles"])


# --- View persistence ---


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between client tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="owner_smiles", password=PASSWORD, email="owner_smiles@correo.com"
    )


@pytest.fixture
def aplicacion(industria):
    return Aplicacion.objects.get_or_create(
        id_industria=industria, nombre_uso="Uso SMILES"
    )[0]


@pytest.fixture
def compuesto(owner, industria):
    """A saved compound whose SMILES is already persisted."""
    call_command("cargar_elementos")
    peso, conteo = calcular_pm(FORMULA_ETANOL)
    compuesto = CompuestoQuimico.objects.create(
        nombre_compuesto="Etanol",
        formula_compuesto=FORMULA_ETANOL,
        id_industria=industria,
        usuario=owner,
        peso_molecular_compuesto=peso,
        smiles=SMILES_ETANOL,
    )
    registrar_elementos_compuesto(compuesto, conteo)
    return compuesto


@pytest.fixture
def relacion(compuesto, aplicacion):
    return CompuestoAplicacion.objects.create(
        id_compuesto=compuesto,
        id_aplicacion=aplicacion,
        concentracion_minima=Decimal("10.00"),
        tipo_concentracion="%p/p",
    )


def _login(client, user):
    # django-axes rejects the direct client.login() helper (same pattern as
    # test_compuesto_update.py / test_force_mfa.py).
    return client.post(
        reverse("login"),
        data={"username": user.username, "password": PASSWORD},
    )


def _relacion_payload(industria, aplicacion):
    return {
        "tipo_industria": industria.pk,
        "id_aplicacion": aplicacion.pk,
        "concentracion_minima": "10.00",
        "tipo_concentracion": "%p/p",
    }


def test_create_view_persists_smiles(client, owner, industria, aplicacion):
    call_command("cargar_elementos")
    _login(client, owner)

    response = client.post(
        reverse("compuesto_crear"),
        data={
            "nombre_compuesto": "Etanol",
            "formula_compuesto": FORMULA_ETANOL,
            "smiles": "CCO",
            **_relacion_payload(industria, aplicacion),
        },
        follow=True,
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto = CompuestoQuimico.objects.get(usuario=owner, nombre_compuesto="Etanol")
    assert compuesto.smiles == "CCO"


def test_create_view_accepts_compound_without_smiles(
    client, owner, industria, aplicacion
):
    call_command("cargar_elementos")
    _login(client, owner)

    response = client.post(
        reverse("compuesto_crear"),
        data={
            "nombre_compuesto": "Etanol",
            "formula_compuesto": FORMULA_ETANOL,
            "smiles": "",
            **_relacion_payload(industria, aplicacion),
        },
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto = CompuestoQuimico.objects.get(usuario=owner, nombre_compuesto="Etanol")
    assert compuesto.smiles is None


def test_update_view_persists_a_new_smiles(
    client, owner, industria, aplicacion, compuesto, relacion
):
    _login(client, owner)

    response = client.post(
        reverse("compuesto_actualizar", kwargs={"pk": compuesto.pk}),
        data={
            "nombre_compuesto": compuesto.nombre_compuesto,
            "formula_compuesto": compuesto.formula_compuesto,
            "smiles": "COC",
            **_relacion_payload(industria, aplicacion),
        },
        follow=True,
    )

    assert response.status_code == 200
    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto.refresh_from_db()
    assert compuesto.smiles == "COC"


def test_update_view_clears_smiles_to_none(
    client, owner, industria, aplicacion, compuesto, relacion
):
    _login(client, owner)

    response = client.post(
        reverse("compuesto_actualizar", kwargs={"pk": compuesto.pk}),
        data={
            "nombre_compuesto": compuesto.nombre_compuesto,
            "formula_compuesto": compuesto.formula_compuesto,
            "smiles": "",
            **_relacion_payload(industria, aplicacion),
        },
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("compuesto_lista")

    compuesto.refresh_from_db()
    assert compuesto.smiles is None
