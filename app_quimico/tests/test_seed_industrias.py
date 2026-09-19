"""Tests for the data migration that seeds the cátedra base rows.

The 0007_seed_industrias_aplicaciones migration runs while the test database is
built, so these tests assert the base rows are present without any extra setup.
Compounds are intentionally NOT seeded.
"""

import pytest

from app_quimico.models import Aplicacion, Industria

pytestmark = pytest.mark.django_db


def test_seed_industrias_cuenta_y_nombres():
    assert Industria.objects.count() == 5

    nombres = set(Industria.objects.values_list("nombre_industria", flat=True))
    assert nombres == {
        "Farmacéutica",
        "Alimenticia",
        "Tratamiento de Aguas",
        "Petroquímica",
        "Metalurgia",
    }


def test_seed_aplicaciones_cuenta():
    assert Aplicacion.objects.count() == 10


def test_seed_aplicaciones_vinculadas_a_su_industria():
    esperado = {
        "Esterilización de Equipos": "Farmacéutica",
        "Solución Salina": "Farmacéutica",
        "Desinfección de Superficies": "Alimenticia",
        "Neutralización de Residuos": "Tratamiento de Aguas",
        "Lubricante de Motor": "Petroquímica",
        "Baño de Galvanizado": "Metalurgia",
    }

    for nombre_uso, nombre_industria in esperado.items():
        aplicacion = Aplicacion.objects.get(nombre_uso=nombre_uso)
        assert aplicacion.id_industria.nombre_industria == nombre_industria
