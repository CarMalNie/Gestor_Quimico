"""Tests del endpoint JSON lookup-isomeros (p2-2d-diagrams-e3-isomeros).

Patrón de test_lookup_endpoint.py (la capa HTTP del cliente PubChem se
parchea — ninguna prueba sale a la red). Contrato completo: 401 JSON
para anónimo, 405 método, 400 fórmula ausente/vacía/larga, 200 con
candidatos [{nombre, smiles}], 404 sin resultados y 502 servicio caído.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

pytestmark = pytest.mark.django_db

PASSWORD = "ClaveSegura123"
CLIENTE = "app_quimico.pubchem_lookup.httpx.Client"
URL_ENDPOINT = reverse("lookup_isomeros")


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
        username="buscador_iso", password=PASSWORD, email="buscadoriso@correo.com"
    )


@pytest.fixture
def logueado(client, usuario):
    client.post(
        reverse("login"),
        data={"username": usuario.username, "password": PASSWORD},
    )
    return client


class FakeRespuesta:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def _cliente_con(respuesta):
    cliente = MagicMock()
    cliente.__enter__ = MagicMock(return_value=cliente)
    cliente.__exit__ = MagicMock(return_value=False)
    cliente.get = MagicMock(return_value=respuesta)
    return MagicMock(return_value=cliente)


def _payload(*propiedades):
    return {"PropertyTable": {"Properties": list(propiedades)}}


class TestAutenticacion:
    def test_anonimo_recibe_401_json_sin_redirect_html(self, client, db):
        respuesta = client.get(URL_ENDPOINT, {"formula": "C2H6O"})

        assert respuesta.status_code == 401
        assert respuesta["Content-Type"] == "application/json"
        assert json.loads(respuesta.content)["error"] == "autenticacion_requerida"

    def test_logueado_no_recibe_401(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"formula": "C2H6O"})
        assert respuesta.status_code != 401


class TestEntrada:
    def test_post_es_405(self, logueado):
        respuesta = logueado.post(URL_ENDPOINT, {"formula": "C2H6O"})
        assert respuesta.status_code == 405

    def test_sin_parametro_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT)
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "formula_requerida"

    def test_formula_vacia_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"formula": "   "})
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "formula_requerida"

    def test_formula_demasiado_larga_es_400(self, logueado):
        respuesta = logueado.get(URL_ENDPOINT, {"formula": "C" * 61})
        assert respuesta.status_code == 400
        assert json.loads(respuesta.content)["error"] == "formula_demasiado_larga"


class TestResolucion:
    def test_formula_con_isomeros_devuelve_lista(self, logueado):
        respuesta = _patch_ok(logueado)
        cuerpo = json.loads(respuesta.content)

        assert respuesta.status_code == 200
        assert cuerpo["fuente"] == "pubchem"
        assert cuerpo["formula"] == "C2H6O"
        assert cuerpo["candidatos"] == [
            {"nombre": "ethanol", "smiles": "CCO"},
            {"nombre": "methoxymethane", "smiles": "COC"},
        ]

    def test_formula_sin_resultados_devuelve_404(self, logueado):
        respuesta = _patch_ok(
            logueado, payload={"PropertyTable": {}}, formula="C999H999"
        )
        assert respuesta.status_code == 404
        cuerpo = json.loads(respuesta.content)
        assert cuerpo["error"] == "no_encontrado"
        assert cuerpo["formula"] == "C999H999"

    def test_pubchem_caido_devuelve_502(self, logueado):
        respuesta = FakeRespuesta(503)
        with patch(CLIENTE, _cliente_con(respuesta)):
            respuesta = logueado.get(URL_ENDPOINT, {"formula": "C2H6O"})
        assert respuesta.status_code == 502
        assert json.loads(respuesta.content)["error"] == "servicio_no_disponible"


def _patch_ok(logueado, payload=None, formula="C2H6O"):
    if payload is None:
        payload = _payload(
            {"CID": 702, "ConnectivitySMILES": "CCO", "IUPACName": "ethanol"},
            {"CID": 8254, "ConnectivitySMILES": "COC", "IUPACName": "methoxymethane"},
        )
    respuesta = FakeRespuesta(200, payload)
    with patch(CLIENTE, _cliente_con(respuesta)):
        return logueado.get(URL_ENDPOINT, {"formula": formula})


def _patch_error_404(logueado):
    with patch(CLIENTE, _cliente_con(FakeRespuesta(404))):
        return logueado.get(URL_ENDPOINT, {"formula": "C999H999"})
