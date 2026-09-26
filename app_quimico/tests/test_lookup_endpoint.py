"""Tests del endpoint JSON lookup-estructura (p2-2d-diagrams-e2-lookup).

La capa HTTP del resolver sigue parcheada (ninguna prueba sale a la red).
Los casos cubren el contrato completo de la vista: login requerido (401
JSON, no redirect HTML), método incorrecto (405), parámetro ausente/vacío/
demasiado largo (400), nombre resuelto (200 con fuente), nombre
desconocido (404 no_encontrado) y upstream caído (502
servicio_no_disponible).
"""

import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
URLOPEN = "app_quimico.estructura_lookup.urllib.request.urlopen"
URL_ENDPOINT = reverse("lookup_estructura")


@pytest.fixture(autouse=True)
def _reset_axes_attempts():
    """Keeps axes lockout counters from leaking between client tests."""
    from axes.models import AccessAttempt

    AccessAttempt.objects.all().delete()
    yield
    AccessAttempt.objects.all().delete()


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="buscador", password=PASSWORD, email="buscador@correo.com"
    )


@pytest.fixture
def logueado(client, usuario):
    client.post(
        reverse("login"),
        data={"username": usuario.username, "password": PASSWORD},
    )
    return client


class TestAutenticacion:
    def test_anonimo_recibe_401_json_sin_redirect_html(self, client, db):
        respuesta = client.get(URL_ENDPOINT, {"nombre": "ethanol"})

        assert respuesta.status_code == 401
        assert respuesta["Content-Type"] == "application/json"
        assert json.loads(respuesta.content)["error"] == "autenticacion_requerida"

    def test_logueado_no_recibe_401(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"nombre": "ethanol"})
        assert respuesta.status_code != 401


class TestEntrada:
    def test_post_es_405(self, logueado):
        respuesta = logueado.post(URL_ENDPOINT, {"nombre": "ethanol"})
        assert respuesta.status_code == 405

    def test_sin_parametro_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT)
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "nombre_requerido"

    def test_nombre_vacio_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"nombre": "   "})
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "nombre_requerido"

    def test_nombre_demasiado_largo_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"nombre": "a" * 201})
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "nombre_demasiado_largo"


class TestResolucion:
    def test_nombre_resuelto_devuelve_smiles_y_fuente(self, logueado):
        respuesta = _patch_ok(logueado, b"CCO\n")
        cuerpo = json.loads(respuesta.content)
        assert respuesta.status_code == 200
        assert cuerpo == {"smiles": "CCO", "fuente": "cactus", "nombre": "ethanol"}

    def test_nombre_desconocido_devuelve_404(self, logueado):
        respuesta = _patch_error_404(logueado)
        assert respuesta.status_code == 404
        cuerpo = json.loads(respuesta.content)
        assert cuerpo["error"] == "no_encontrado"
        assert cuerpo["nombre"] == "sustancia inexistente"

    def test_upstream_caido_devuelve_502(self, logueado):
        respuesta = _patch_down(logueado)
        assert respuesta.status_code == 502
        assert json.loads(respuesta.content)["error"] == "servicio_no_disponible"


def _patch_ok(logueado, body):
    class _Resp:
        status = 200

        def read(self, *args):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    with patch(URLOPEN, return_value=_Resp()):
        return logueado.get(URL_ENDPOINT, {"nombre": "ethanol"})


def _patch_error(status):
    import io
    import urllib.error

    return urllib.error.HTTPError(
        "https://cactus.nci.nih.gov/x", status, "error", {}, io.BytesIO(b"")
    )


def _patch_error_404(logueado):
    with patch(URLOPEN, side_effect=_patch_error(404)):
        return logueado.get(URL_ENDPOINT, {"nombre": "sustancia inexistente"})


def _patch_down(logueado):
    with patch(URLOPEN, side_effect=_patch_error(503)):
        return logueado.get(URL_ENDPOINT, {"nombre": "ethanol"})
