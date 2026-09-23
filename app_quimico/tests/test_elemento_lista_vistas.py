"""Tests for the view-mode toggle (vista=tarjetas|tabla) of ElementoListView."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from app_quimico.models import CATEGORIA_CHOICES, ElementoQuimico

pytestmark = pytest.mark.django_db


@pytest.fixture
def elementos_cargados():
    """Carga los 118 elementos IUPAC para las pruebas de la vista de lista."""
    call_command("cargar_elementos")


def test_vista_por_defecto_es_tarjetas(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"))

    assert respuesta.status_code == 200
    assert respuesta.context["vista"] == "tarjetas"


def test_vista_tarjetas_mantiene_filtrado_del_servidor(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"categoria": "Gases Nobles"})

    assert respuesta.status_code == 200
    assert respuesta.context["vista"] == "tarjetas"

    elementos = list(respuesta.context["elementos"])
    assert 0 < len(elementos) < ElementoQuimico.objects.count()
    assert all(
        elemento.detalleelemento.categoria_elemento == "Gases Nobles"
        for elemento in elementos
    )


def test_vista_tabla_devuelve_los_118_ordenados_por_numero_atomico(
    client, elementos_cargados
):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    assert respuesta.status_code == 200
    assert respuesta.context["vista"] == "tabla"

    numeros = [elemento.numero_atomico_elemento for elemento in respuesta.context["elementos"]]
    assert len(numeros) == 118
    assert numeros == sorted(numeros)


@pytest.mark.parametrize(
    "parametros",
    [
        {"min_peso_atomico": "100"},
        {"busqueda_nombre": "no-existe-xyz"},
        {"categoria": "Gases Nobles"},
    ],
)
def test_vista_tabla_ignora_los_filtros_del_servidor(client, elementos_cargados, parametros):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla", **parametros})

    assert respuesta.status_code == 200
    assert len(list(respuesta.context["elementos"])) == 118


def test_vista_desconocida_cae_en_tarjetas(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "xyz"})

    assert respuesta.status_code == 200
    assert respuesta.context["vista"] == "tarjetas"


def test_contexto_expone_las_categorias_canonicas(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    categorias = list(respuesta.context["categorias"])
    assert len(categorias) == 12
    assert [valor for valor, _ in categorias] == [valor for valor, _ in CATEGORIA_CHOICES]
