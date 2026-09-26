"""Cliente PubChem fastformula para el selector de isómeros.

Feature p2-2d-diagrams-e3-isomeros (Entrega 3). Dada una fórmula
molecular, devuelve la lista de isómeros {nombre, smiles} que PubChem
conoce, para que el usuario elija su estructura.

Acceso: PubChem rechaza clientes Python HTTP/1.1 con 503 (fingerprint
anti-abuse, verificado en PA y local), pero **httpx con HTTP/2 pasa
limpio** (spike verificado local y en PA, 200 HTTP/2). Se usa un Client
por consulta: el volumen es mínimo (form de portafolio) y evita estado
compartido entre requests del proceso web.

El dedupe por SMILES conserva el primer IUPACName de cada estructura:
PubChem devuelve varios CIDs por el mismo grafo (isotólogos, sales) y el
nombre del primero es el más común (ethanol, no un isotopólogo).
"""

import json

import httpx
from pysmiles import read_smiles

PUBCHEM_FASTFORMULA_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/fastformula"
    "/{formula}/property/CanonicalSMILES,IUPACName/JSON"
)
PUBCHEM_TIMEOUT_SEGUNDOS = 8
USER_AGENT = "gestor-quimico/1.0 (portfolio; Django)"
MAX_CANDIDATOS = 10

# Campos que PubChem usa para el SMILES según la versión del endpoint:
_SMILES_KEYS = ("CanonicalSMILES", "ConnectivitySMILES", "SMILES")


class IsomerosNoEncontrados(Exception):
    """La fórmula no arrojó ningún resultado en PubChem (404 upstream)."""


class PubChemNoDisponible(Exception):
    """PubChem no respondió utilizable: timeout, red o 5xx/503 upstream."""


def buscar_isomeros(formula):
    """Devuelve la lista dedupada [{nombre, smiles}] para la fórmula.

    `formula` llega normalizada desde la vista. Dedupe por SMILES
    (conserva el primer IUPACName), cap MAX_CANDIDATOS. Levanta
    IsomerosNoEncontrados / PubChemNoDisponible tipadas.
    """
    url = PUBCHEM_FASTFORMULA_URL.format(formula=_codificar_formula(formula))

    try:
        with httpx.Client(http2=True, timeout=PUBCHEM_TIMEOUT_SEGUNDOS) as cliente:
            respuesta = cliente.get(url, headers={"User-Agent": USER_AGENT})
    except (httpx.HTTPError, OSError) as exc:
        raise PubChemNoDisponible(str(exc)) from exc

    if respuesta.status_code == 404:
        raise IsomerosNoEncontrados(formula)
    if respuesta.status_code >= 400:
        raise PubChemNoDisponible(f"HTTP {respuesta.status_code}")

    try:
        cuerpo = respuesta.json()
        propiedades = cuerpo.get("PropertyTable", {}).get("Properties") or []
    except (json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError) as exc:
        # Respuesta 200 que no trae la estructura esperada (JSONDecodeError
        # es subclase de ValueError): tratar como servicio degradado, no
        # como 500 del propio endpoint.
        raise PubChemNoDisponible("respuesta inesperada de PubChem") from exc

    candidatos = []
    vistos = set()
    for prop in propiedades:
        smiles = _primer_smiles(prop)
        if not smiles or smiles in vistos:
            continue
        vistos.add(smiles)
        candidatos.append({"nombre": prop.get("IUPACName", ""), "smiles": smiles})
        if len(candidatos) >= MAX_CANDIDATOS:
            break

    if not candidatos:
        raise IsomerosNoEncontrados(formula)
    return candidatos


def _primer_smiles(propiedad):
    for clave in _SMILES_KEYS:
        valor = propiedad.get(clave)
        if valor and _es_smiles_valido(valor):
            return valor
    return None


def _es_smiles_valido(candidato):
    """Mismo criterio de aceptación que el form y el resolver de Cactus:
    sin espacios internos, parseable con pysmiles y con al menos un átomo."""
    if not candidato or any(char.isspace() for char in candidato):
        return False
    try:
        mol = read_smiles(candidato)
    except Exception:
        return False
    return mol is not None and len(mol.nodes) > 0


def _codificar_formula(formula):
    import urllib.parse

    return urllib.parse.quote(formula, safe="")
