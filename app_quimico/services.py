"""Domain services for compound chemistry calculations.

Views orchestrate HTTP concerns only; formula parsing, PM quantization and
ElementoCompuesto bookkeeping live here so create/update share one tested
implementation."""

from decimal import Decimal

from app_quimico.models import ElementoCompuesto, ElementoQuimico
from app_quimico.utils import CalculadoraPM

# PM stored with 4 decimal places, matching the model field definition.
_PM_QUANTUM = Decimal("0.0001")


def calcular_pm(formula):
    """Parses a formula and returns (peso_molecular, elementos_conteo).

    Surrounding whitespace is tolerated (copy-paste is common); internal
    whitespace stays invalid under strict IUPAC syntax.
    peso_molecular is a Decimal quantized to the stored precision.
    Raises ValueError with a user-friendly Spanish message for invalid input.
    """
    formula = formula.strip()
    pm_float, elementos_conteo = CalculadoraPM().analizar_formula(formula)
    peso = Decimal(str(pm_float)).quantize(_PM_QUANTUM)
    return peso, elementos_conteo


def registrar_elementos_compuesto(compuesto, elementos_conteo):
    """(Re)writes the ElementoCompuesto rows of a SAVED compound from a parsed
    element count map. Unknown symbols are skipped (defensive; the parser
    already rejects them)."""
    if compuesto.pk is None:
        raise ValueError("El compuesto debe estar guardado antes de registrar sus elementos.")

    ElementoCompuesto.objects.filter(id_compuesto=compuesto).delete()

    simbolos = elementos_conteo.keys()
    elementos_map = {
        e.simbolo_elemento: e
        for e in ElementoQuimico.objects.filter(simbolo_elemento__in=simbolos)
    }

    elementos_a_crear = [
        ElementoCompuesto(
            id_compuesto=compuesto,
            id_elemento=elementos_map[simbolo],
            cantidad_elem_en_comp=cantidad,
        )
        for simbolo, cantidad in elementos_conteo.items()
        if simbolo in elementos_map
    ]
    ElementoCompuesto.objects.bulk_create(elementos_a_crear)
