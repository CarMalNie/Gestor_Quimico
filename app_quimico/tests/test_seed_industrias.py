"""Tests for the data migrations that seed the industrial catalog.

The 0007_seed_industrias_aplicaciones (cátedra base rows) and
0008_seed_industrias_aplicaciones_expansion (operator-approved expansion)
migrations run while the test database is built, so these tests assert the
seeded rows are present without any extra setup. Compounds are intentionally
NOT seeded.
"""

import pytest

from app_quimico.models import Aplicacion, Industria

pytestmark = pytest.mark.django_db

# Rows seeded by 0007_seed_industrias_aplicaciones (cátedra base).
INDUSTRIAS_BASE = {
    "Farmacéutica",
    "Alimenticia",
    "Tratamiento de Aguas",
    "Petroquímica",
    "Metalurgia",
}

APLICACIONES_BASE = {
    "Esterilización de Equipos": "Farmacéutica",
    "Solución Salina": "Farmacéutica",
    "Desinfección de Superficies": "Alimenticia",
    "Estabilización de pH": "Alimenticia",
    "Neutralización de Residuos": "Tratamiento de Aguas",
    "Adición de Cloro": "Tratamiento de Aguas",
    "Lubricante de Motor": "Petroquímica",
    "Control de Corrosión": "Petroquímica",
    "Baño de Galvanizado": "Metalurgia",
    "Limpieza Ácida de Metales": "Metalurgia",
}

# Rows seeded by 0008_seed_industrias_aplicaciones_expansion.
INDUSTRIAS_EXPANSION = {
    "Agroquímica",
    "Cosmética e Higiene",
    "Construcción",
    "Automotriz",
    "Textil",
    "Pinturas y Recubrimientos",
    "Cuidado del Hogar",
    "Laboratorio y Docencia",
}

APLICACIONES_EXPANSION = {
    "Fertilización Nitrogenada": "Agroquímica",
    "Control de Malezas": "Agroquímica",
    "Ajuste de pH de Suelos": "Agroquímica",
    "Fungicida Foliar": "Agroquímica",
    "Ajuste de pH de Cosméticos": "Cosmética e Higiene",
    "Conservación de Formulaciones": "Cosmética e Higiene",
    "Antitranspirantes": "Cosmética e Higiene",
    "Exfoliación Química": "Cosmética e Higiene",
    "Acelerante de Hormigón": "Construcción",
    "Limpieza de Superficies de Obra": "Construcción",
    "Fabricación de Vidrio": "Construcción",
    "Electrolito de Baterías": "Automotriz",
    "Refrigeración de Motores": "Automotriz",
    "Limpiador de Frenos": "Automotriz",
    "Blanqueo de Fibras": "Textil",
    "Fijación de Tintes": "Textil",
    "Neutralización de Baños de Tintura": "Textil",
    "Pigmentación Blanca": "Pinturas y Recubrimientos",
    "Disolución de Resinas": "Pinturas y Recubrimientos",
    "Desengrasado Metálico": "Pinturas y Recubrimientos",
    "Desinfección Doméstica": "Cuidado del Hogar",
    "Removedor de Sarro": "Cuidado del Hogar",
    "Limpieza Multiusos": "Cuidado del Hogar",
    "Preparación de Reactivos": "Laboratorio y Docencia",
    "Estandarización de Soluciones": "Laboratorio y Docencia",
    "Indicadores de pH": "Laboratorio y Docencia",
}


def test_seed_industrias_cuenta_total():
    assert Industria.objects.count() == 13


def test_seed_aplicaciones_cuenta_total():
    assert Aplicacion.objects.count() == 36


def test_seed_industrias_base_nombres():
    nombres = set(Industria.objects.values_list("nombre_industria", flat=True))
    assert INDUSTRIAS_BASE <= nombres

    for nombre in INDUSTRIAS_BASE:
        assert Industria.objects.filter(nombre_industria=nombre).exists()


def test_seed_industrias_expansion_nombres():
    nombres = set(Industria.objects.values_list("nombre_industria", flat=True))
    assert INDUSTRIAS_EXPANSION <= nombres

    for nombre in INDUSTRIAS_EXPANSION:
        assert Industria.objects.filter(nombre_industria=nombre).exists()


def test_seed_aplicaciones_base_vinculadas_a_su_industria():
    for nombre_uso, nombre_industria in APLICACIONES_BASE.items():
        aplicacion = Aplicacion.objects.get(nombre_uso=nombre_uso)
        assert aplicacion.id_industria.nombre_industria == nombre_industria


def test_seed_aplicaciones_expansion_vinculadas_a_su_industria():
    for nombre_uso, nombre_industria in APLICACIONES_EXPANSION.items():
        aplicacion = Aplicacion.objects.get(nombre_uso=nombre_uso)
        assert aplicacion.id_industria.nombre_industria == nombre_industria
