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
    assert "/compuestos/api/lookup-estructura/" in form_html
    assert "Buscar estructura por nombre" in form_html


def test_form_tiene_mensajes_y_fallback_pubchem(form_html):
    assert 'id="lookup-mensaje"' in form_html
    assert 'id="lookup-pubchem"' in form_html
    assert "pubchem.ncbi.nlm.nih.gov" in form_html
    assert 'target="_blank"' in form_html


def test_form_carga_el_script_cache_busteado(form_html):
    assert "js/estructura_lookup.js?v=1" in form_html


def test_el_js_maneja_los_tres_desenlaces():
    js = LOOKUP_JS.read_text(encoding="utf-8")

    # Éxito: rellena el input y pide revisión antes de guardar.
    assert "Estructura cargada" in js
    # 404: fallback manual a PubChem con el nombre precargado.
    assert "No se encontró una estructura" in js
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
