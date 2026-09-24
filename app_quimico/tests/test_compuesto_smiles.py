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


def test_form_rejects_smiles_that_parse_to_an_atomless_graph():
    """pysmiles is lenient: 'XYZ' raises nothing and yields an empty graph,
    so an atom-less result must be rejected explicitly."""
    form = CompuestoQuimicoForm(data=_form_data(smiles="XYZ"))

    assert not form.is_valid()
    assert "smiles" in form.errors
    assert ERROR_SMILES in str(form.errors["smiles"])


def test_form_still_accepts_empty_smiles_as_opt_out_after_atomless_hardening():
    """The empty/whitespace opt-out path is resolved before parsing and stays
    valid even though 0-node graphs are now rejected."""
    vacio = CompuestoQuimicoForm(data=_form_data(smiles=""))
    espacios = CompuestoQuimicoForm(data=_form_data(smiles="   "))

    assert vacio.is_valid(), vacio.errors
    assert vacio.cleaned_data["smiles"] is None
    assert espacios.is_valid(), espacios.errors
    assert espacios.cleaned_data["smiles"] is None


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


# ========================================================================= #
# T4 — Staged "¿Agregar estructura 2D?" form UX (compuesto_form.html)
# ========================================================================= #

COMPUESTO_FORM_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "app_quimico"
    / "compuesto_quimico"
    / "compuesto_form.html"
)


def _crear_form_html(client, user):
    _login(client, user)
    response = client.get(reverse("compuesto_crear"))
    assert response.status_code == 200
    return response.content.decode()


def test_form_template_uses_a_shared_staged_flow(client, owner, compuesto, relacion):
    """Create and edit render the same template, so the staged flow is shared."""
    assert COMPUESTO_FORM_TEMPLATE.exists()

    crear = _crear_form_html(client, owner)
    editar = client.get(
        reverse("compuesto_actualizar", kwargs={"pk": compuesto.pk})
    )
    assert editar.status_code == 200
    html = editar.content.decode()

    for marker in (
        "¿Agregar estructura 2D?",
        'id="estructura2d"',
        'id="smiles-ayuda"',
        'id="smiles-opt-out"',
    ):
        assert marker in crear, marker
        assert marker in html, marker


def test_form_template_starts_with_a_collapsed_entry_button(client, owner):
    html = _crear_form_html(client, owner)

    assert "¿Agregar estructura 2D?" in html
    assert 'data-bs-toggle="collapse"' in html
    assert 'data-bs-target="#estructura2d"' in html
    assert 'aria-expanded="false"' in html
    assert 'id="estructura2d"' in html
    # Nothing chemical is visible until the entry button is clicked.
    assert 'class="collapse show"' not in html


def test_form_template_keeps_the_smiles_input_inside_the_collapsed_section(
    client, owner
):
    html = _crear_form_html(client, owner)

    section_at = html.index('id="estructura2d"')
    input_at = html.index('id="id_smiles"')
    assert section_at < input_at
    assert 'name="smiles"' in html


def test_form_template_has_the_didactic_help_accordion(client, owner):
    html = _crear_form_html(client, owner)

    assert "¿Qué es esto?" in html
    assert 'id="smiles-ayuda"' in html
    assert "Simplified Molecular Input Line Entry Specification" in html
    # Ethanol vs dimethyl ether: same atoms, different connectivity.
    assert "CH3-CH2-OH" in html
    assert "CH3-O-CH3" in html


def test_form_template_has_the_opt_out_button_wired_to_the_input(client, owner):
    html = _crear_form_html(client, owner)

    assert "No — mejor sin estructura" in html
    assert 'id="smiles-opt-out"' in html
    assert 'id="id_smiles"' in html


def test_form_template_autopens_the_section_when_smiles_has_errors(client, owner):
    _login(client, owner)

    response = client.post(
        reverse("compuesto_crear"),
        data={
            "nombre_compuesto": "Etanol",
            "formula_compuesto": FORMULA_ETANOL,
            "smiles": "XYZ",
        },
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert 'class="collapse show"' in html
    assert 'aria-expanded="true"' in html
    assert ERROR_SMILES in html


# ========================================================================= #
# T5 — Render de la estructura 2D (SmilesDrawer) en lista y detalle
# ========================================================================= #

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPUESTO_LISTA_TEMPLATE = (
    PROJECT_ROOT
    / "app_quimico"
    / "templates"
    / "app_quimico"
    / "compuesto_quimico"
    / "compuesto_lista.html"
)
COMPUESTO_DETALLE_TEMPLATE = (
    PROJECT_ROOT
    / "app_quimico"
    / "templates"
    / "app_quimico"
    / "compuesto_quimico"
    / "compuesto_detalle.html"
)
SMILES_RENDER_JS = PROJECT_ROOT / "static" / "js" / "smiles_render.js"
SMILESDRAWER_VENDOR = (
    PROJECT_ROOT
    / "static"
    / "vendor"
    / "smilesdrawer"
    / "smiles-drawer.min.js"
)
BASE_TEMPLATE = PROJECT_ROOT / "templates" / "base.html"


@pytest.fixture
def compuesto_sin_smiles(owner, industria):
    """A saved compound owned by ``owner`` whose SMILES is empty."""
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Metano",
        formula_compuesto="CH4",
        id_industria=industria,
        usuario=owner,
        peso_molecular_compuesto=Decimal("16.0430"),
    )


def _lista_html(client, user):
    _login(client, user)
    response = client.get(reverse("compuesto_lista"))
    assert response.status_code == 200
    return response.content.decode()


def _detalle_html(client, user, compuesto):
    _login(client, user)
    response = client.get(
        reverse("compuesto_detalle", kwargs={"pk": compuesto.pk})
    )
    assert response.status_code == 200
    return response.content.decode()


# --- Lista de compuestos (tarjetas) ---


def test_lista_without_smiles_keeps_the_card_unchanged(
    client, owner, compuesto_sin_smiles
):
    html = _lista_html(client, owner)

    assert compuesto_sin_smiles.nombre_compuesto in html
    # Sin SMILES no hay bloque de estructura ni atributo de render.
    assert "estructura-2d" not in html
    assert 'data-smiles="' not in html
    # La tarjeta existente sigue intacta.
    assert "card h-100 shadow-sm border-primary" in html
    assert "Detalles Químicos:" in html
    assert "CH4" in html


def test_lista_with_smiles_renders_the_estructura_2d_block(
    client, owner, compuesto
):
    html = _lista_html(client, owner)

    assert "estructura-2d" in html
    assert f'data-smiles="{SMILES_ETANOL}"' in html
    assert "Estructura 2D (SMILES)" in html
    # Scripts self-hosted con cache-bust, solo en esta página.
    assert "vendor/smilesdrawer/smiles-drawer.min.js" in html
    assert "js/smiles_render.js" in html
    assert "?v=1" in html


# --- Detalle del compuesto ---


def test_detalle_without_smiles_is_untouched(client, owner, compuesto_sin_smiles):
    html = _detalle_html(client, owner, compuesto_sin_smiles)

    assert "estructura-2d" not in html
    assert "estructura2d-tab" not in html
    assert 'data-smiles="' not in html
    # Pestañas existentes intactas y sin scripts extra.
    assert 'id="composition-tab"' in html
    assert 'id="applications-tab"' in html
    assert "smiles-drawer.min.js" not in html
    assert "smiles_render.js" not in html


def test_detalle_with_smiles_renders_the_estructura_2d_tab(
    client, owner, compuesto
):
    html = _detalle_html(client, owner, compuesto)

    assert 'id="estructura2d-tab"' in html
    assert 'data-bs-target="#estructura2d"' in html
    assert 'id="estructura2d"' in html
    assert f'data-smiles="{SMILES_ETANOL}"' in html
    assert "Estructura 2D (SMILES)" in html
    assert "vendor/smilesdrawer/smiles-drawer.min.js" in html
    assert "smiles_render.js?v=1" in html


# --- Regresión: comentarios multilinea {# #} ---
#
# Django {# #} comenta una sola línea: un bloque que abre y cierra en líneas
# distintas no es un comentario y se renderiza como texto visible. Mismo
# defecto que p1-periodic-table T7; los bloques se eliminan en vez de
# convertirlos en comentarios de una línea.


def test_lista_with_smiles_does_not_leak_multiline_template_comments(
    client, owner, compuesto
):
    """La tarjeta con SMILES no debe mostrar el texto de los {# #} multilinea."""
    html = _lista_html(client, owner)

    assert "Estructura 2D opcional" not in html
    assert "SmilesDrawer solo se carga" not in html
    # El bloque real de estructura sigue renderizado (no se borró de más).
    assert "Estructura 2D (SMILES)" in html
    assert f'data-smiles="{SMILES_ETANOL}"' in html


def test_detalle_with_smiles_does_not_leak_multiline_template_comments(
    client, owner, compuesto
):
    """La página de detalle con SMILES no debe mostrar esos comentarios."""
    html = _detalle_html(client, owner, compuesto)

    assert "pestaña Estructura 2D solo existe" not in html
    assert "SmilesDrawer se carga solo cuando" not in html
    # La pestaña real de estructura sigue renderizada.
    assert 'id="estructura2d-tab"' in html
    assert f'data-smiles="{SMILES_ETANOL}"' in html


# --- Assets y contrato del renderer (sin runner JS) ---


def test_vendored_smilesdrawer_asset_is_present():
    assert SMILESDRAWER_VENDOR.exists()
    assert SMILESDRAWER_VENDOR.stat().st_size > 0


def test_smiles_render_js_uses_the_vendored_svg_drawer_api():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    # Batch sobre los contenedores, API v2 del bundle vendoreado.
    assert "[data-smiles]" in source
    assert "SmilesDrawer.SvgDrawer" in source
    assert "SmilesDrawer.parse" in source
    # Fail-soft si el global no está disponible.
    assert 'typeof SmilesDrawer === "undefined"' in source
    assert 'drawer.draw(tree, svg, "light")' in source


def test_smiles_scripts_are_not_loaded_globally_in_base():
    base = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "smiles-drawer.min.js" not in base
    assert "smiles_render.js" not in base


def test_base_stylesheet_cache_bust_was_bumped():
    # styles.css cambió (sección .estructura-2d): el ?v sube para invalidar
    # la caché del navegador (convención del proyecto: bump al editar assets).
    source = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "css/styles.css' %}?v=3" in source
