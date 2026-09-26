"""Tests del cliente PubChem fastformula (p2-2d-diagrams-e3-isomeros).

La capa HTTP se parchea a nivel ``httpx.Client`` (ninguna prueba sale a
la red). Cubre: parseo feliz con dedupe por SMILES, cap de candidatos,
campos SMILES defensivos (Canonical/Connectivity/SMILES), fórmula
codificada en el URL, 404 -> IsomerosNoEncontrados, 503/500 ->
PubChemNoDisponible, timeout -> PubChemNoDisponible, y cuerpo 200
inesperado -> PubChemNoDisponible.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app_quimico import pubchem_lookup
from app_quimico.pubchem_lookup import (
    IsomerosNoEncontrados,
    PubChemNoDisponible,
    buscar_isomeros,
)

CLIENTE = "app_quimico.pubchem_lookup.httpx.Client"


class FakeRespuesta:
    def __init__(self, status=200, payload=None, body=b"no-json"):
        self.status_code = status
        self._payload = payload
        self._body = body

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _cliente_con(respuesta):
    cliente = MagicMock()
    cliente.__enter__ = MagicMock(return_value=cliente)
    cliente.__exit__ = MagicMock(return_value=False)
    cliente.get = MagicMock(return_value=respuesta)
    return MagicMock(return_value=cliente)


def _payload(*propiedades):
    return {"PropertyTable": {"Properties": list(propiedades)}}


def test_fastformula_resuelve_isomeros_con_dedupe():
    """CIDs distintos con el mismo grafo se colapsan: queda el primer nombre."""
    respuesta = FakeRespuesta(
        200,
        _payload(
            {"CID": 702, "ConnectivitySMILES": "CCO", "IUPACName": "ethanol"},
            {"CID": 8254, "ConnectivitySMILES": "COC", "IUPACName": "methoxymethane"},
            {"CID": 102138, "ConnectivitySMILES": "CCO", "IUPACName": "1,1,1,2,2-pentadeuterio-2-deuteriooxyethane"},
        ),
    )
    with patch(CLIENTE, _cliente_con(respuesta)) as cliente:
        candidatos = buscar_isomeros("C2H6O")

    assert candidatos == [
        {"nombre": "ethanol", "smiles": "CCO"},
        {"nombre": "methoxymethane", "smiles": "COC"},
    ]
    url = cliente.return_value.get.call_args[0][0]
    assert "fastformula/C2H6O" in url
    assert cliente.return_value.get.call_args[1]["headers"]["User-Agent"] == pubchem_lookup.USER_AGENT


def test_cap_de_candidatos_y_dedupe_conserva_el_primer_nombre():
    propiedades = [
        {"CID": n, "SMILES": "CC" + "C" * n, "IUPACName": f"n{n}"}
        for n in range(1, 15)
    ]
    respuesta = FakeRespuesta(200, _payload(*propiedades))
    with patch(CLIENTE, _cliente_con(respuesta)):
        candidatos = buscar_isomeros("C14H30")

    assert len(candidatos) == pubchem_lookup.MAX_CANDIDATOS
    assert candidatos[0]["nombre"] == "n1"
    assert candidatos[-1]["nombre"] == f"n{pubchem_lookup.MAX_CANDIDATOS}"


def test_parsea_cualquiera_de_los_tres_campos_smiles():
    for clave in ("CanonicalSMILES", "ConnectivitySMILES", "SMILES"):
        respuesta = FakeRespuesta(200, _payload({clave: "CCO", "IUPACName": "ethanol"}))
        with patch(CLIENTE, _cliente_con(respuesta)):
            assert buscar_isomeros("C2H6O") == [
                {"nombre": "ethanol", "smiles": "CCO"}
            ]


def test_smiles_no_utilizable_se_ignora():
    respuesta = FakeRespuesta(
        200,
        _payload(
            {"CID": 1, "ConnectivitySMILES": "C C", "IUPACName": "basura"},  # espacios
            {"CID": 2, "ConnectivitySMILES": "CCO", "IUPACName": "ethanol"},
        ),
    )
    with patch(CLIENTE, _cliente_con(respuesta)):
        candidatos = buscar_isomeros("C2H6O")
    assert candidatos == [{"nombre": "ethanol", "smiles": "CCO"}]


def test_sin_propiedades_utilizables_es_no_encontradas():
    respuesta = FakeRespuesta(200, {"PropertyTable": {}})
    with patch(CLIENTE, _cliente_con(respuesta)):
        with pytest.raises(IsomerosNoEncontrados):
            buscar_isomeros("C999H999")


def test_upstream_404_es_no_encontradas():
    respuesta = FakeRespuesta(404)
    with patch(CLIENTE, _cliente_con(respuesta)):
        with pytest.raises(IsomerosNoEncontrados):
            buscar_isomeros("C999H999")


def test_upstream_503_es_no_disponible():
    respuesta = FakeRespuesta(503)
    with patch(CLIENTE, _cliente_con(respuesta)):
        with pytest.raises(PubChemNoDisponible):
            buscar_isomeros("C2H6O")


def test_timeout_es_no_disponible():
    cliente = MagicMock()
    cliente.__enter__ = MagicMock(return_value=cliente)
    cliente.__exit__ = MagicMock(return_value=False)
    cliente.get = MagicMock(side_effect=httpx.ConnectTimeout("tiempo agotado"))
    with patch(CLIENTE, MagicMock(return_value=cliente)):
        with pytest.raises(PubChemNoDisponible):
            buscar_isomeros("C2H6O")


def test_json_inesperado_es_no_disponible():
    respuesta = FakeRespuesta(200, body=b"ok")
    with patch(CLIENTE, _cliente_con(respuesta)):
        with pytest.raises(PubChemNoDisponible):
            buscar_isomeros("C2H6O")
