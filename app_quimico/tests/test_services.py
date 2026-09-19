"""Unit tests for the domain service layer (PM calculation + element rows)."""

import pytest
from decimal import Decimal

from app_quimico.models import (
    CompuestoQuimico, ElementoCompuesto, ElementoQuimico, Industria,
)
from app_quimico.services import calcular_pm, registrar_elementos_compuesto

pytestmark = pytest.mark.django_db


@pytest.fixture
def elemento_hidrogeno():
    from decimal import Decimal
    return ElementoQuimico.objects.create(
        nombre_elemento="Hidrogeno",
        simbolo_elemento="H",
        numero_atomico_elemento=1,
        peso_atomico_elemento=Decimal("1.0080"),
    )


@pytest.fixture
def elemento_oxigeno():
    from decimal import Decimal
    return ElementoQuimico.objects.create(
        nombre_elemento="Oxigeno",
        simbolo_elemento="O",
        numero_atomico_elemento=8,
        peso_atomico_elemento=Decimal("15.9990"),
    )


@pytest.fixture
def compuesto_guardado(elemento_hidrogeno, elemento_oxigeno):
    from django.contrib.auth.models import User

    usuario = User.objects.create_user(username="dueño", password="pass12345")
    industria = Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]
    return CompuestoQuimico.objects.create(
        nombre_compuesto="Agua",
        formula_compuesto="H2O",
        id_industria=industria,
        usuario=usuario,
        peso_molecular_compuesto="18.0150",
    )


def test_calcular_pm_devuelve_decimal_cuantizado(elemento_hidrogeno, elemento_oxigeno):
    peso, conteo = calcular_pm("H2O")
    assert peso == Decimal("18.0150")
    assert conteo == {"H": 2, "O": 1}


def test_registrar_elementos_crea_filas(compuesto_guardado):
    _, conteo = calcular_pm("H2O")
    registrar_elementos_compuesto(compuesto_guardado, conteo)

    filas = ElementoCompuesto.objects.filter(id_compuesto=compuesto_guardado)
    assert filas.count() == 2
    cantidades = {f.id_elemento.simbolo_elemento: f.cantidad_elem_en_comp for f in filas}
    assert cantidades == {"H": 2, "O": 1}


def test_registrar_elementos_reemplaza_filas_previas(compuesto_guardado):
    _, conteo = calcular_pm("H2O")
    registrar_elementos_compuesto(compuesto_guardado, conteo)
    registrar_elementos_compuesto(compuesto_guardado, conteo)

    filas = ElementoCompuesto.objects.filter(id_compuesto=compuesto_guardado)
    assert filas.count() == 2  # no duplicates after re-registration


def test_registrar_elementos_requiere_compuesto_guardado():
    with pytest.raises(ValueError, match="guardado"):
        registrar_elementos_compuesto(CompuestoQuimico(), {})
