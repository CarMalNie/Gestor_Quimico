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
from pysmiles import read_smiles
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
from app_quimico.utils import expandir_heteroatomos

pytestmark = pytest.mark.django_db

MIGRATION_NAME = "0010_compuestoquimico_smiles"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SMILES_ETANOL = "CCO"
# T9: el SMILES que alimenta el dibujo ya no es el almacenado, sino el
# expandido (los H de O/N/S pasan a ser [H] explícitos).
EXPANDIDO_ETANOL = "[H]OCC"


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
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html
    assert "Estructura 2D (SMILES)" in html
    # Scripts self-hosted con cache-bust, solo en esta página.
    assert "vendor/smilesdrawer/smiles-drawer.min.js" in html
    assert "js/smiles_render.js" in html
    assert "?v=2" in html


def test_form_template_cache_busts_the_cascade_script(client, owner):
    """compuesto_cascade.js se sirve con version cache-bust en el form."""
    html = _crear_form_html(client, owner)

    assert "compuesto_cascade.js?v=1" in html

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
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html
    assert "Estructura 2D (SMILES)" in html
    assert "vendor/smilesdrawer/smiles-drawer.min.js" in html
    assert "smiles_render.js?v=2" in html


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
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html


def test_detalle_with_smiles_does_not_leak_multiline_template_comments(
    client, owner, compuesto
):
    """La página de detalle con SMILES no debe mostrar esos comentarios."""
    html = _detalle_html(client, owner, compuesto)

    assert "pestaña Estructura 2D solo existe" not in html
    assert "SmilesDrawer se carga solo cuando" not in html
    # La pestaña real de estructura sigue renderizada.
    assert 'id="estructura2d-tab"' in html
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html


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


# ========================================================================= #
# T7 — Didactic bond-type caption (model classification + templates)
# ========================================================================= #
#
# Agreed B+ design: the parsed SMILES graph decides the caption. Multiple
# disconnected fragments ('.') or a nonzero net charge over the whole graph
# mean the declared species is ionic, and every fragment is listed as a
# species label with its net charge as a unicode superscript (Hill order:
# C, H, then alphabetical). A single neutral fragment is covalent, even when
# it carries internal formal charges (zwitterion) — the classification is
# orientative and the form help confesses it. The internal covalent bonds of
# a polyatomic ion stay visible in the drawing and are never restated here.

CAPTION_IONICA_NACL = "Estructura iónica: Na⁺ · Cl⁻"
CAPTION_IONICA_NACLO = "Estructura iónica: Na⁺ · ClO⁻"
CAPTION_IONICA_CLO = "Estructura iónica: ClO⁻"
CAPTION_COVALENTE = "Enlace covalente"


def _clasificar(smiles):
    """Classification is pure over ``self.smiles``: no DB row needed."""
    return CompuestoQuimico(smiles=smiles).clasificar_enlace_smiles()


# --- Clasificación (unidad) ---


def test_ionic_multi_fragment_lists_each_species():
    assert _clasificar("[Na+].[Cl-]") == CAPTION_IONICA_NACL


def test_ionic_polyatomic_ion_lists_only_the_species_not_its_internal_bond():
    # NaClO: Na⁺ plus the hypochlorite ion. The Cl-O bond belongs to the
    # drawing; the caption only names the separated species.
    assert _clasificar("[Na+].[O-]Cl") == CAPTION_IONICA_NACLO


def test_ionic_repeated_species_are_deduplicated():
    assert _clasificar("[Na+].[Cl-].[Na+]") == CAPTION_IONICA_NACL


def test_ionic_single_fragment_with_nonzero_net_charge_is_still_ionic():
    # Declared alone, a net -1 fragment honestly describes an ion.
    assert _clasificar("[O-]Cl") == CAPTION_IONICA_CLO


def test_ionic_species_label_includes_implicit_hydrogens():
    # Hydroxide must read HO⁻ (Hill order, no carbon) instead of a misleading
    # bare O⁻ (which would describe an oxide).
    assert _clasificar("[Na+].[OH-]") == "Estructura iónica: Na⁺ · HO⁻"


def test_covalent_single_neutral_fragment():
    assert _clasificar("CCO") == CAPTION_COVALENTE


def test_covalent_single_atom():
    assert _clasificar("O") == CAPTION_COVALENTE


def test_zwitterion_is_reported_as_covalent():
    # Net charge 0 on one connected fragment: documented orientative rule.
    assert _clasificar("[NH3+]CC(=O)[O-]") == CAPTION_COVALENTE


@pytest.mark.parametrize("valor", [None, "", "   ", "\t\n "])
def test_missing_smiles_has_no_caption(valor):
    assert _clasificar(valor) is None


@pytest.mark.parametrize("valor", ["XYZ", "C1CC", "(", "[Na+].[", "1"])
def test_unparsable_smiles_has_no_caption_and_never_raises(valor):
    assert _clasificar(valor) is None


# --- Template: tarjeta de la lista ---


@pytest.fixture
def compuesto_ionico(owner, industria):
    """A saved ionic compound (table salt) owned by ``owner``."""
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Cloruro de sodio",
        formula_compuesto="NaCl",
        id_industria=industria,
        usuario=owner,
        smiles="[Na+].[Cl-]",
    )


def test_lista_shows_the_ionic_caption(client, owner, compuesto_ionico):
    html = _lista_html(client, owner)

    # La sección sigue identificándose y debajo aparece la clasificación.
    assert "Estructura 2D (SMILES)" in html
    assert CAPTION_IONICA_NACL in html


def test_lista_shows_the_covalent_caption(client, owner, compuesto):
    html = _lista_html(client, owner)

    assert "Estructura 2D (SMILES)" in html
    assert CAPTION_COVALENTE in html


def test_lista_without_smiles_shows_no_bond_caption(
    client, owner, compuesto_sin_smiles
):
    html = _lista_html(client, owner)

    assert CAPTION_COVALENTE not in html
    assert "Estructura iónica" not in html


def test_lista_with_unparsable_smiles_shows_the_diagram_without_caption(
    client, owner, industria
):
    # El form no permite guardar esto, pero una fila vieja/manual no debe
    # romper el render: el diagrama sigue y la clasificación se omite.
    CompuestoQuimico.objects.create(
        nombre_compuesto="Roto",
        formula_compuesto="CH4",
        id_industria=industria,
        usuario=owner,
        smiles="C1CC",
    )
    html = _lista_html(client, owner)

    assert 'data-smiles="C1CC"' in html
    assert "Estructura 2D (SMILES)" in html
    assert CAPTION_COVALENTE not in html
    assert "Estructura iónica" not in html


# --- Template: detalle ---


def test_detalle_shows_the_ionic_caption(client, owner, compuesto_ionico):
    html = _detalle_html(client, owner, compuesto_ionico)

    assert "Estructura 2D (SMILES)" in html
    assert CAPTION_IONICA_NACL in html


def test_detalle_shows_the_covalent_caption(client, owner, compuesto):
    html = _detalle_html(client, owner, compuesto)

    assert "Estructura 2D (SMILES)" in html
    assert CAPTION_COVALENTE in html


def test_detalle_without_smiles_shows_no_bond_caption(
    client, owner, compuesto_sin_smiles
):
    html = _detalle_html(client, owner, compuesto_sin_smiles)

    assert CAPTION_COVALENTE not in html
    assert "Estructura iónica" not in html


# --- Template: ayuda orientativa del form ---


def test_form_help_confesses_the_orientative_nature(client, owner):
    html = _crear_form_html(client, owner)

    assert "La clasificación del enlace es orientativa" in html
    assert "zwitterion" in html.lower()
    # La ayuda previa sigue presente (no se reemplazó copy existente).
    assert "Es opcional: sin ella el compuesto funciona igual que siempre." in html


# ========================================================================= #
# T9 — Expansión selectiva de H de O/N/S a [H] para el dibujo 2D
# ========================================================================= #
#
# Agreed option C: server-side, only the implicit hydrogens attached to
# O/N/S become explicit ``[H]`` atoms so the drawer shows H-O-H for water
# while C-bound H stays condensed. The stored SMILES and the T7 caption logic
# are untouched; only ``data-smiles`` is fed the expanded string. pysmiles
# cannot emit ``[H]`` through its public writer (``write_smiles`` strips them
# via ``remove_explicit_hydrogens``), so the helper tags the added H nodes
# with ``isotope=''`` and a post-write guard falls back to the original
# SMILES whenever ``[H]`` is missing.

SMILES_AGUA = "O"
EXPANDIDO_AGUA = "[H]O[H]"
SMILES_GLUCOSA = "OCC1OC(O)C(O)C(O)C1O"


def _grafo_explicito(smiles):
    """Re-parse keeping explicit ``[H]`` as real nodes for structural asserts."""
    return read_smiles(smiles, zero_order_bonds=False, explicit_hydrogen=True)


def _nodos_h(grafo):
    return [n for n, d in grafo.nodes(data=True) if d.get('element') == 'H']


def _h_sobre_heteroatomos(grafo):
    """H (en el re-parse) unidos a un O/N/S.

    Los H escritos explícitamente cuelgan de un heteroátomo (al que la
    expansión le dejó ``hcount`` en cero, así que el re-parse no agrega H
    implícito ahí); los H implícitos de carbono sí aparecen como nodos con
    ``explicit_hydrogen=True``, pero cuelgan de un C y quedan fuera.
    """
    hetero = {
        n for n, d in grafo.nodes(data=True)
        if d.get('element') in {'O', 'N', 'S'}
    }
    return [h for h in _nodos_h(grafo) if next(iter(grafo[h])) in hetero]


# --- Unidad: expansión ---


def test_expandir_heteroatomos_expande_el_agua_a_dos_h():
    resultado = expandir_heteroatomos(SMILES_AGUA)
    grafo = _grafo_explicito(resultado)

    assert resultado.count('[H]') == 2
    assert grafo.number_of_nodes() == 3
    oxigenos = [n for n, d in grafo.nodes(data=True) if d.get('element') == 'O']
    assert len(oxigenos) == 1
    hidrogenos = _nodos_h(grafo)
    assert len(hidrogenos) == 2
    enlaces_oh = list(grafo.edges(oxigenos[0]))
    assert len(enlaces_oh) == 2
    assert all(grafo.edges[e].get('order') == 1 for e in enlaces_oh)


def test_expandir_heteroatomos_expande_los_cinco_oh_de_la_glucosa():
    resultado = expandir_heteroatomos(SMILES_GLUCOSA)
    grafo = _grafo_explicito(resultado)

    # 5 OH (el O del éter de anillo no aporta H); el enunciado "6" era off-by-one.
    assert resultado.count('[H]') == 5
    # Todos los [H] escritos cuelgan de un O/N/S; ninguno de un carbono.
    assert len(_h_sobre_heteroatomos(grafo)) == 5
    carbonos = [n for n, d in grafo.nodes(data=True) if d.get('element') == 'C']
    assert len(carbonos) == 6


def test_expandir_heteroatomos_no_agrega_h_al_hipoclorito_con_carga():
    # O⁻: la carga consume el electrón que si no sería un H.
    resultado = expandir_heteroatomos("[Na+].[O-]Cl")
    grafo = _grafo_explicito(resultado)

    assert _nodos_h(grafo) == []
    oxigenos = [n for n, d in grafo.nodes(data=True) if d.get('element') == 'O']
    assert len(oxigenos) == 1
    assert grafo.nodes[oxigenos[0]].get('charge') == -1
    elementos = {d.get('element') for _, d in grafo.nodes(data=True)}
    assert {'Na', 'O', 'Cl'} <= elementos


def test_expandir_heteroatomos_expande_el_oh_del_etanol_y_deja_los_c_condensados():
    resultado = expandir_heteroatomos(SMILES_ETANOL)
    grafo = _grafo_explicito(resultado)

    assert resultado.count('[H]') == 1
    assert len(_h_sobre_heteroatomos(grafo)) == 1
    carbonos = [n for n, d in grafo.nodes(data=True) if d.get('element') == 'C']
    assert len(carbonos) == 2


def test_expandir_heteroatomos_no_toca_los_hidrogenos_del_carbono():
    resultado = expandir_heteroatomos("c1ccccc1")
    grafo = _grafo_explicito(resultado)

    assert resultado.count('[H]') == 0
    assert sum(1 for _, d in grafo.nodes(data=True) if d.get('element') == 'C') == 6


def test_expandir_heteroatomos_no_expande_el_n_de_valencia_completa():
    # N con dos dobles enlaces (orden 4 > valencia 3): no admite H.
    resultado = expandir_heteroatomos("O=N(=O)O")
    grafo = _grafo_explicito(resultado)

    assert len(_nodos_h(grafo)) == 1  # solo el O terminal con H
    n_nodo = [n for n, d in grafo.nodes(data=True) if d.get('element') == 'N'][0]
    assert all(grafo.nodes[v].get('element') != 'H' for v in grafo[n_nodo])


@pytest.mark.parametrize("valor", [None, "", "   ", "XYZ", "C1CC", "(", "[Na+].["])
def test_expandir_heteroatomos_devuelve_la_entrada_sin_usar(valor):
    # Defensivo: entrada vacía/None o no parseable se devuelve tal cual,
    # nunca levanta y nunca devuelve None inesperado.
    assert expandir_heteroatomos(valor) == valor


def test_contrato_de_expansion_emite_h_explicito_o_falla_ruidosamente():
    """Guarda anti-upgrade de pysmiles.

    La expansión depende de que ``remove_explicit_hydrogens`` de pysmiles
    2.1.0 no borre los H marcados con ``isotope=''``. Si una actualización
    cambia esa condición, la guarda interna devuelve el SMILES original y
    este test falla de forma visible en lugar de degradar en silencio.
    """
    assert "[H]" in expandir_heteroatomos(SMILES_AGUA)


# --- Modelo: smiles_para_render ---


def test_smiles_para_render_expande_los_heteroatomos():
    compuesto = CompuestoQuimico(smiles=SMILES_AGUA)

    assert "[H]" in compuesto.smiles_para_render()


def test_smiles_para_render_sin_smiles_devuelve_cadena_vacia():
    assert CompuestoQuimico(smiles=None).smiles_para_render() == ""
    assert CompuestoQuimico(smiles="").smiles_para_render() == ""


def test_smiles_para_render_devuelve_el_original_si_no_es_parseable():
    # Una fila vieja/manual no debe romper el render.
    compuesto = CompuestoQuimico(smiles="C1CC")

    assert compuesto.smiles_para_render() == "C1CC"


# --- Plantillas: data-smiles expandido + caption T7 intacto ---


@pytest.fixture
def compuesto_agua(owner, industria):
    """Agua: un único heteroátomo con hidrógenos implícitos."""
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Agua",
        formula_compuesto="H2O",
        id_industria=industria,
        usuario=owner,
        smiles=SMILES_AGUA,
    )


def test_lista_renderiza_el_agua_con_h_explicitos(client, owner, compuesto_agua):
    html = _lista_html(client, owner)

    assert f'data-smiles="{EXPANDIDO_AGUA}"' in html
    # La clasificación T7 sigue leyendo el SMILES original: agua = covalente.
    assert CAPTION_COVALENTE in html


def test_detalle_renderiza_el_agua_con_h_explicitos(client, owner, compuesto_agua):
    html = _detalle_html(client, owner, compuesto_agua)

    assert f'data-smiles="{EXPANDIDO_AGUA}"' in html
    assert CAPTION_COVALENTE in html
