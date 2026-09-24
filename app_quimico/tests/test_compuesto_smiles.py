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

from pathlib import Path

import pytest
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import TextField

from app_quimico.models import CompuestoQuimico, Industria

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
