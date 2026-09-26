"""Endpoint JSON del lookup de estructura por nombre.

Feature p2-2d-diagrams-e2-lookup (Entrega 2). La vista solo traduce
HTTP: normaliza el parámetro `nombre`, llama al resolver de
`estructura_lookup.py` y mapea sus excepciones tipadas a respuestas
JSON diferenciadas (200 / 400 / 401 / 404 / 405 / 502). Para un frontend
JS no conviene el redirect HTML de @login_required: anónimo recibe 401
JSON y el form le muestra el pedido de login.
"""

import json

from django.http import HttpResponse

from app_quimico.estructura_lookup import (
    LookupNoDisponible,
    LookupNoEncontrado,
    resolver_smiles,
)
from app_quimico.pubchem_lookup import (
    IsomerosNoEncontrados,
    PubChemNoDisponible,
    buscar_isomeros,
)


def lookup_estructura(request):
    """GET /compuestos/api/lookup-estructura/?nombre=<nombre del compuesto>."""
    if not request.user.is_authenticated:
        return json_response(401, {"error": "autenticacion_requerida"})

    if request.method != "GET":
        return json_response(405, {"error": "metodo_no_permitido"})

    nombre = (request.GET.get("nombre") or "").strip()
    if not nombre:
        return json_response(400, {"error": "nombre_requerido"})

    if len(nombre) > 200:
        return json_response(400, {"error": "nombre_demasiado_largo"})

    try:
        smiles = resolver_smiles(nombre)
    except LookupNoEncontrado:
        return json_response(404, {"error": "no_encontrado", "nombre": nombre})
    except LookupNoDisponible:
        return json_response(502, {"error": "servicio_no_disponible"})

    return json_response(200, {"smiles": smiles, "fuente": "cactus", "nombre": nombre})


def lookup_isomeros(request):
    """GET /compuestos/api/lookup-isomeros/?formula=<formula molecular>.

    Entrega 3: lista de isómeros con nombre para que el usuario elija su
    estructura (la fórmula es idioma-agnóstico y ya es obligatoria en el
    form). Cap de candidatos lo aplica el cliente de PubChem.
    """
    if not request.user.is_authenticated:
        return json_response(401, {"error": "autenticacion_requerida"})

    if request.method != "GET":
        return json_response(405, {"error": "metodo_no_permitido"})

    formula = (request.GET.get("formula") or "").strip()
    if not formula:
        return json_response(400, {"error": "formula_requerida"})

    if len(formula) > 60:
        return json_response(400, {"error": "formula_demasiado_larga"})

    try:
        candidatos = buscar_isomeros(formula)
    except IsomerosNoEncontrados:
        return json_response(404, {"error": "no_encontrado", "formula": formula})
    except PubChemNoDisponible:
        return json_response(502, {"error": "servicio_no_disponible"})

    return json_response(
        200, {"formula": formula, "fuente": "pubchem", "candidatos": candidatos}
    )


def json_response(status, payload):
    """Respuesta JSON uniforme (facilita los asserts de los tests)."""
    return HttpResponse(
        json.dumps(payload), status=status, content_type="application/json"
    )
