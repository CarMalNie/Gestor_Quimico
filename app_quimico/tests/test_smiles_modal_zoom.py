"""Modal de zoom del diagrama 2D (p2-2d-diagrams-e4-modal-zoom).

Contratos cubiertos:
- El renderer client-side reutiliza un core de dibujo (``dibujarSvg``) y delega
  todo el ciclo de vida del modal a Bootstrap 5
  (``bootstrap.Modal.getOrCreateInstance``), sin reimplementar abrir/cerrar.
- La tarjeta de la lista y la pestaña del detalle exponen un disparador por
  click/teclado (``data-smiles-zoom``) y un botón visible "Ampliar"
  (``data-smiles-ampliar``).
- UN solo modal compartido por página (``id="modal-estructura-2d"``), fuera del
  loop de tarjetas.
- Sin SMILES no hay disparador, ni botón, ni modal, ni cambios en la tarjeta.
- Assets cache-busteados y CSS del modal (cursor zoom-in + fondo blanco fijo).

Estilo del proyecto: asserts de contrato sobre el archivo fuente y sobre el
HTML renderizado (como test_compuesto_smiles.py / test_estructura_lookup_frontend.py).
No hay runner de JS en CI, así que el contrato del renderer se verifica por
fuente.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from axes.models import AccessAttempt
from django.contrib.auth.models import User
from django.urls import reverse

from app_quimico.models import CompuestoQuimico, Industria

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
SMILES_ETANOL = "CCO"
# El ``data-smiles`` que alimenta el dibujo es el expandido (H de O/N/S a [H]).
EXPANDIDO_ETANOL = "[H]OCC"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SMILES_RENDER_JS = PROJECT_ROOT / "static" / "js" / "smiles_render.js"
STYLES_CSS = PROJECT_ROOT / "static" / "css" / "styles.css"
BASE_TEMPLATE = PROJECT_ROOT / "templates" / "base.html"
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

MODAL_ID = 'id="modal-estructura-2d"'


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between client tests."""
    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def industria():
    return Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="owner_zoom", password=PASSWORD, email="owner_zoom@correo.com"
    )


def _crear(industria, owner, nombre, formula, peso, smiles=None):
    return CompuestoQuimico.objects.create(
        nombre_compuesto=nombre,
        formula_compuesto=formula,
        id_industria=industria,
        usuario=owner,
        peso_molecular_compuesto=Decimal(peso),
        smiles=smiles,
    )


@pytest.fixture
def compuesto_etanol(industria, owner):
    return _crear(industria, owner, "Etanol", "C2H6O", "46.0690", SMILES_ETANOL)


@pytest.fixture
def compuesto_sin_smiles(industria, owner):
    return _crear(industria, owner, "Metano", "CH4", "16.0430")


def _login(client, user):
    # django-axes rejects the direct client.login() helper (project pattern).
    return client.post(
        reverse("login"),
        data={"username": user.username, "password": PASSWORD},
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


def _bloque_css(source, selector):
    """Devuelve el cuerpo de la primera regla que empieza con ``selector``."""
    inicio = source.index(selector)
    fin = source.index("}", inicio)
    return source[inicio:fin]


# ========================================================================= #
# Renderer (static/js/smiles_render.js) — contrato por fuente
# ========================================================================= #


def test_js_define_un_core_de_dibujo_reutilizable_y_reutiliza_el_centrado():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    # Core extraído de renderOne y reusado por miniatura y modal.
    assert "function dibujarSvg" in source
    assert source.count("dibujarSvg(") >= 2
    assert "centrarContenido" in source


def test_js_delega_el_ciclo_del_modal_a_bootstrap5():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    # Cero JS custom de modal: BS5 nativo vía getOrCreateInstance + show().
    assert "bootstrap.Modal.getOrCreateInstance" in source
    assert ".show()" in source
    assert "modal-estructura-2d" in source
    # El cierre (X, ESC, click fuera) queda del lado de BS5.
    assert "Escape" not in source


def test_js_dibuja_el_modal_a_600x450():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    assert "600" in source
    assert "450" in source


def test_js_mantiene_el_guard_fail_soft_y_el_mensaje_del_modal():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    # Guard existente intacto (smoke de la Entrega 1).
    assert 'typeof SmilesDrawer === "undefined"' in source
    # Disparadores soportados.
    assert "data-smiles-zoom" in source
    assert "data-smiles-ampliar" in source
    # Fail-soft visible cuando el dibujo no se puede generar.
    assert "No se pudo generar la estructura 2D" in source


def test_js_soporta_click_y_teclado_sobre_el_disparador():
    source = SMILES_RENDER_JS.read_text(encoding="utf-8")

    # Enter/Espacio para el contenedor con tabindex (los botones ya emiten click).
    assert '"Enter"' in source
    assert '" "' in source
    assert 'addEventListener("click"' in source
    assert 'addEventListener("keydown"' in source


# ========================================================================= #
# Lista — tarjeta
# ========================================================================= #


def test_lista_con_smiles_expone_disparador_boton_y_modal(
    client, owner, compuesto_etanol
):
    html = _lista_html(client, owner)

    # Disparador sobre el diagrama + botón visible de accesibilidad.
    assert "data-smiles-zoom" in html
    assert f'data-smiles-ampliar="{EXPANDIDO_ETANOL}"' in html
    assert "Ampliar" in html
    # El diagrama sigue siendo la miniatura intacta.
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html
    # Un único modal compartido.
    assert html.count(MODAL_ID) == 1


def test_lista_comparte_un_unico_modal_entre_varias_tarjetas(
    client, owner, industria, compuesto_etanol
):
    _crear(industria, owner, "Agua", "H2O", "18.0153", "O")
    _crear(industria, owner, "Metanol", "CH4O", "32.0420", "CO")

    html = _lista_html(client, owner)

    # El modal NO se duplica por tarjeta...
    assert html.count(MODAL_ID) == 1
    # ...pero cada tarjeta con SMILES conserva su disparador.
    assert html.count("data-smiles-zoom") == 3


def test_lista_emite_el_modal_aunque_el_primer_compuesto_no_tenga_smiles(
    client, owner, industria
):
    # Orden por nombre: "Aaa" (sin SMILES) queda antes que "Zzz" (con SMILES).
    # El modal debe emitirse igual: la guarda es "algún compuesto con SMILES",
    # no "el primero".
    _crear(industria, owner, "Aaa sin estructura", "CH4", "16.0430")
    _crear(industria, owner, "Zzz etanol", "C2H6O", "46.0690", SMILES_ETANOL)

    html = _lista_html(client, owner)

    assert "data-smiles-zoom" in html
    assert html.count(MODAL_ID) == 1


def test_lista_sin_smiles_no_agrega_zoom_ni_modal(
    client, owner, compuesto_sin_smiles
):
    html = _lista_html(client, owner)

    assert "data-smiles-zoom" not in html
    assert "data-smiles-ampliar" not in html
    assert MODAL_ID not in html
    # La tarjeta sigue exactamente como hoy (assert de la Entrega 1).
    assert "estructura-2d" not in html
    assert "card h-100 shadow-sm border-primary" in html


# ========================================================================= #
# Detalle — pestaña Estructura 2D
# ========================================================================= #


def test_detalle_con_smiles_expone_disparador_boton_y_modal(
    client, owner, compuesto_etanol
):
    html = _detalle_html(client, owner, compuesto_etanol)

    assert "data-smiles-zoom" in html
    assert f'data-smiles-ampliar="{EXPANDIDO_ETANOL}"' in html
    assert "Ampliar" in html
    assert html.count(MODAL_ID) == 1
    # La pestaña y la miniatura siguen intactas.
    assert 'id="estructura2d"' in html
    assert f'data-smiles="{EXPANDIDO_ETANOL}"' in html


def test_detalle_sin_smiles_no_agrega_zoom_ni_modal(
    client, owner, compuesto_sin_smiles
):
    html = _detalle_html(client, owner, compuesto_sin_smiles)

    assert "data-smiles-zoom" not in html
    assert "data-smiles-ampliar" not in html
    assert MODAL_ID not in html
    assert "estructura-2d" not in html


# ========================================================================= #
# Modal — shell nativo Bootstrap 5
# ========================================================================= #


def test_el_modal_usa_el_shell_nativo_de_bootstrap5(client, owner, compuesto_etanol):
    html = _lista_html(client, owner)

    assert MODAL_ID in html
    assert "modal fade" in html
    assert "modal-dialog modal-lg modal-dialog-centered" in html
    # Cierre provisto por BS5 (X con data-bs-dismiss) y accesibilidad.
    assert 'data-bs-dismiss="modal"' in html
    assert 'aria-labelledby="modal-estructura-2d-titulo"' in html
    assert 'id="modal-estructura-2d-titulo"' in html
    assert "Estructura 2D ampliada" in html
    # Contenedor de dibujo del modal (fondo claro fijo en CSS).
    assert "estructura-2d-modal" in html
    assert "data-smiles-modal-body" in html


def test_los_templates_declaran_el_modal_compartido():
    """Contrato de plantilla: el id del modal es el mismo en lista y detalle."""
    lista = COMPUESTO_LISTA_TEMPLATE.read_text(encoding="utf-8")
    detalle = COMPUESTO_DETALLE_TEMPLATE.read_text(encoding="utf-8")

    assert lista.count('id="modal-estructura-2d"') == 1
    assert detalle.count('id="modal-estructura-2d"') == 1


# ========================================================================= #
# Assets: cache-bust
# ========================================================================= #


def test_scripts_de_smiles_van_cache_busteados_a_v3(client, owner, compuesto_etanol):
    lista = _lista_html(client, owner)
    detalle = _detalle_html(client, owner, compuesto_etanol)

    assert "js/smiles_render.js?v=3" in lista
    assert "js/smiles_render.js?v=3" in detalle


def test_base_hoja_de_estilos_cache_bust_a_v4():
    source = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert "css/styles.css' %}?v=4" in source


# ========================================================================= #
# CSS
# ========================================================================= #


def test_css_marca_el_diagrama_como_clickeable():
    source = STYLES_CSS.read_text(encoding="utf-8")

    assert "cursor: zoom-in" in _bloque_css(source, ".estructura-2d {")


def test_css_del_modal_con_fondo_blanco_fijo_y_sin_estiramiento():
    source = STYLES_CSS.read_text(encoding="utf-8")

    contenedor = _bloque_css(source, ".estructura-2d-modal {")
    assert "#ffffff" in contenedor
    svg = _bloque_css(source, ".estructura-2d-modal svg {")
    # Escala proporcional (height auto), nunca un SVG estirado.
    assert "height: auto" in svg
