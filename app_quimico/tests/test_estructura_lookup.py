"""Tests del lookup de estructura por nombre (p2-2d-diagrams-e2-lookup).

La capa HTTP está parcheada (``urllib.request.urlopen``) igual que en
``test_brevo_api_email.py``: ninguna prueba sale a la red real. Se cubren
los tres desenlaces del resolver (éxito, nombre desconocido, servicio caído)
y el guard de validación pysmiles sobre la respuesta upstream.
"""

import io
import urllib.parse
import urllib.error
from unittest.mock import patch

import pytest

from app_quimico import estructura_lookup
from app_quimico.estructura_lookup import (
    CACTUS_URL_TEMPLATE,
    LookupNoDisponible,
    LookupNoEncontrado,
    resolver_smiles,
)

URLOPEN = "app_quimico.estructura_lookup.urllib.request.urlopen"


class FakeResponse:
    """Stand-in mínimo del context manager que devuelve urlopen."""

    def __init__(self, body=""):
        self.status = 200
        self._body = body.encode("utf-8")

    def read(self, size=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _http_error(status):
    return urllib.error.HTTPError(
        CACTUS_URL_TEMPLATE.format(nombre="x"), status, "error", {}, io.BytesIO(b"")
    )


def _abrir(body="CCO", status=200):
    if status != 200:
        exc = _http_error(status)
        return None, exc
    return FakeResponse(body), None


@pytest.mark.parametrize(
    "nombre,cuerpo,esperado",
    [
        ("ethanol", "CCO\n", "CCO"),
        ("sodium chloride", "[Na+].[Cl-]", "[Na+].[Cl-]"),
        ("glucose", "OC[C@@H](O)[C@@H](O)[C@H](O)[C@@H](O)C=O\n", None),
    ],
)
def test_resuelve_smiles_validos(nombre, cuerpo, esperado):
    if esperado is None:
        esperado = cuerpo.strip()
    with patch(URLOPEN, return_value=FakeResponse(cuerpo)) as urlopen:
        assert resolver_smiles(nombre) == esperado
    url_usada = urlopen.call_args[0][0].full_url
    assert "cactus.nci.nih.gov" in url_usada
    assert urllib.parse.quote(nombre) in url_usada
    assert urlopen.call_args[0][0].headers["User-agent"] == estructura_lookup.USER_AGENT


def test_respuesta_multilinea_usa_la_primera_linea():
    with patch(URLOPEN, return_value=FakeResponse("CCO\ntexto extra")):
        assert resolver_smiles("ethanol") == "CCO"


def test_upstream_404_es_no_encontrado():
    with patch(URLOPEN, side_effect=_http_error(404)):
        with pytest.raises(LookupNoEncontrado):
            resolver_smiles("nonexistentsubstancexyz")


def test_upstream_500_es_no_disponible():
    with patch(URLOPEN, side_effect=_http_error(500)):
        with pytest.raises(LookupNoDisponible):
            resolver_smiles("ethanol")


def test_timeout_es_no_disponible():
    with patch(URLOPEN, side_effect=TimeoutError("tiempo agotado")):
        with pytest.raises(LookupNoDisponible):
            resolver_smiles("ethanol")


def test_cuerpo_de_error_de_cactus_es_no_encontrado():
    # Cactus a veces responde 200 con el cuerpo "ERROR: ...".
    with patch(URLOPEN, return_value=FakeResponse("ERROR: not found")):
        with pytest.raises(LookupNoEncontrado):
            resolver_smiles("nonexistentsubstancexyz")


@pytest.mark.parametrize(
    "cuerpo",
    ["XYZ", "", "C C", "no es un smiles"],
)
def test_cuerpo_no_utilizable_es_no_encontrado(cuerpo):
    with patch(URLOPEN, return_value=FakeResponse(cuerpo)):
        with pytest.raises(LookupNoEncontrado):
            resolver_smiles("algo")


def test_url_codifica_los_espacios_del_nombre():
    with patch(URLOPEN, return_value=FakeResponse("CCO")) as urlopen:
        resolver_smiles("sodium chloride")
    url_usada = urlopen.call_args[0][0].full_url
    assert "sodium%20chloride" in url_usada
