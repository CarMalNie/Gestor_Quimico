"""Lookup de estructura 2D (SMILES) por nombre de compuesto.

Feature p2-2d-diagrams-e2-lookup (Entrega 2). El motor único es el
Cactus resolver del NCI/CADD (`cactus.nci.nih.gov`), verificado estable
desde PythonAnywhere (spike 23:54, HTTP 200 en 0.1s; dominio cubierto
por la wildcard `.nih.gov` de la whitelist de cuentas free). PubChem
queda reservado para el fallback manual del frontend: su API rechaza
clientes Python con 503 (fingerprint anti-abuse, verificado en PA).

El resultado NUNCA se entrega sin validar: el SMILES devuelto por el
resolver se re-parsea con pysmiles (misma lógica que el form) para no
propagar basura al renderer.
"""

import urllib.error
import urllib.parse
import urllib.request

from pysmiles import read_smiles

CACTUS_URL_TEMPLATE = "https://cactus.nci.nih.gov/chemical/structure/{nombre}/smiles"
CACTUS_TIMEOUT_SEGUNDOS = 8
USER_AGENT = "gestor-quimico/1.0 (portfolio; Django)"

# Tipos de fallo que la vista traduce a respuestas JSON diferenciadas:
#   LookupNoEncontrado  -> 404 no_encontrado
#   LookupNoDisponible  -> 502 servicio_no_disponible
class LookupNoEncontrado(Exception):
    """El resolver no conoce el nombre consultado (upstream 404)."""


class LookupNoDisponible(Exception):
    """El resolver no respondió: timeout, red o 5xx upstream."""


def resolver_smiles(nombre):
    """Devuelve el SMILES validado para `nombre`, o levanta las excepciones
    tipadas de arriba.

    `nombre` ya viene normalizado (strip) desde la vista. El valor devuelto
    pasa por pysmiles antes de entregarse: un upstream que responda texto
    no-SMILES se trata como nombre no encontrado, no como resultado.
    """
    url = CACTUS_URL_TEMPLATE.format(nombre=urllib.parse.quote(nombre))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(request, timeout=CACTUS_TIMEOUT_SEGUNDOS) as response:
            cuerpo = response.read(4096).decode("utf-8", errors="replace").strip()
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 404, 500):
            # Cactus "no conozco esa estructura": 404 REST o 500 con página
            # "Page not found" (verificado 2026-09-26 con nombres basura y
            # nombres en español: glucosa/aspirina/bicarbonato -> 500). Todo
            # ese rango es "nombre desconocido", no falla de servicio.
            raise LookupNoEncontrado(nombre) from exc
        raise LookupNoDisponible(f"HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LookupNoDisponible(str(exc)) from exc

    if not cuerpo or cuerpo.upper().startswith("ERROR"):
        raise LookupNoEncontrado(nombre)

    smiles = cuerpo.splitlines()[0].strip() if cuerpo else ""
    if not _es_smiles_valido(smiles):
        # Upstream contestó algo que no es una estructura utilizable.
        raise LookupNoEncontrado(nombre)

    return smiles


def _es_smiles_valido(candidato):
    """Misma lógica de aceptación que el form: sin espacios internos (pysmiles
    parsea "C C" como dos átomos desconectados en vez de fallar), parseable
    con pysmiles y con al menos un átomo (pysmiles es tolerante con tokens
    desconocidos y devuelve un grafo vacío en vez de fallar)."""
    if not candidato or any(char.isspace() for char in candidato):
        return False
    try:
        mol = read_smiles(candidato)
    except Exception:
        return False
    return mol is not None and len(mol.nodes) > 0
