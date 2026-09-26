"""Frontend del lookup de estructura: wiring del form (p2-2d-diagrams-e2-lookup).

Asserts de plantilla renderizada (patrón de test_compuesto_smiles): el botón
con su endpoint, el contenedor de mensajes y el enlace de fallback a PubChem
deben existir en el form, y el script nueva va cache-busteado (?v=1).
El texto de fallback manual NO puede faltar en el JS (es la red de seguridad
cuando Cactus no resuelve).
"""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

PASSWORD = "ClaveSegura123"
LOOKUP_JS = Path(__file__).resolve().parents[2] / "static" / "js" / "estructura_lookup.js"
COMPUESTO_FORM_TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "app_quimico"
    / "compuesto_quimico"
    / "compuesto_form.html"
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        username="dueño_lookup", password=PASSWORD, email="duenio@correo.com"
    )


@pytest.fixture
def form_html(client, owner):
    client.post(
        reverse("login"),
        data={"username": owner.username, "password": PASSWORD},
    )
    respuesta = client.get(reverse("compuesto_crear"))
    assert respuesta.status_code == 200
    return respuesta.content.decode()


def test_form_tiene_boton_lookup_con_endpoint_del_server(form_html):
    assert 'id="smiles-buscar"' in form_html
    assert "data-lookup-url=" in form_html
    assert "/compuestos/api/lookup-isomeros/" in form_html
    assert "Buscar estructura (por fórmula)" in form_html


def test_form_tiene_mensajes_y_fallback_pubchem(form_html):
    assert 'id="lookup-mensaje"' in form_html
    assert 'id="lookup-pubchem"' in form_html
    assert "pubchem.ncbi.nlm.nih.gov" in form_html
    assert 'target="_blank"' in form_html


def test_el_fallback_pubchem_arranca_oculto_sin_utility_de_display():
    """El link de fallback solo aparece en 404/502: 'hidden' no puede estar
    pisado por d-inline-block (display utility con !important de BS5)."""
    html = COMPUESTO_FORM_TEMPLATE.read_text(encoding="utf-8")
    desde = html.index('id="lookup-pubchem"')
    tag = html[desde : html.index(">", desde)]

    assert "hidden" in tag
    assert "d-inline-block" not in tag


def test_form_carga_el_script_cache_busteado(form_html):
    assert "js/estructura_lookup.js?v=3" in form_html


def test_el_fallback_pregunta_no_se_encuentra_en_la_plantilla(form_html):
    """Feedback del operador (E3 producción): el enlace manual también debe
    estar disponible cuando la lista de isómeros aparece pero el compuesto
    no está entre los candidatos. Pregunta universal en la plantilla."""
    assert "¿No se encuentra? Abrir la búsqueda en PubChem" in form_html


def test_el_js_muestra_el_enlace_junto_a_la_lista_de_isomeros():
    js = LOOKUP_JS.read_text(encoding="utf-8")

    # mostrarCandidatos invoca el enlace manual tras renderizar la lista.
    dentro_de_mostrar_candidatos = js.index("function mostrarCandidatos")
    fin_funcion = js.index("\n  function usarCandidatoDirecto", dentro_de_mostrar_candidatos)
    bloque = js[dentro_de_mostrar_candidatos:fin_funcion]
    assert "enlacePubChemConFormula(formula)" in bloque


def test_el_js_maneja_los_tres_desenlaces_y_el_selector():
    js = LOOKUP_JS.read_text(encoding="utf-8")

    # Un solo isómero: rellena directo.
    assert "candidatos.length === 1" in js
    # Varios: lista de opciones clickeables con nombre + SMILES.
    assert "list-group-item-action" in js
    assert "Elija la que corresponde a su compuesto" in js
    # 404: fallback manual a PubChem con la fórmula precargada (no el nombre).
    assert "No se encontraron estructuras para la fórmula" in js
    assert "encodeURIComponent" in js
    # 502/red: servicio no disponible, mismo fallback manual.
    assert "servicio de búsqueda" in js
    # Fail soft: sin los elementos del DOM no pasa nada.
    assert "return;" in js


def test_el_copy_del_js_es_espanol_neutro():
    """Decisión del operador: UI sin voseo, neutra para la cátedra."""
    js = LOOKUP_JS.read_text(encoding="utf-8")

    for prohibido in ("sabés", " buscá", " probá", " editá", " revísá"):
        assert prohibido not in js
    assert "Revísela y edítela" in js


def test_el_boton_vive_dentro_de_la_seccion_2d_plegada():
    """El lookup pertenece a la UX escalonada: no se ve sin abrir la sección."""
    html = COMPUESTO_FORM_TEMPLATE.read_text(encoding="utf-8")
    seccion = html.index('id="estructura2d"')
    boton = html.index('id="smiles-buscar"')
    assert seccion < boton
    # Y antes del cierre de la card de estructura (opt-out es el último botón).
    opt_out = html.index('id="smiles-opt-out"')
    assert boton < opt_out


def test_el_boton_lee_la_formula_del_form():
    """La búsqueda por fórmula lee el campo obligatorio formula_compuesto."""
    html = COMPUESTO_FORM_TEMPLATE.read_text(encoding="utf-8")

    assert 'id="lookup-resultados"' in html
    # El JS usa el campo de fórmula (no el de nombre).
    js = LOOKUP_JS.read_text(encoding="utf-8")
    assert 'id_formula_compuesto' in js
