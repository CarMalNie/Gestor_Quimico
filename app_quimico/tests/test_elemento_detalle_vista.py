"""Tests for the element detail template: units and data conventions."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from app_quimico.models import ElementoQuimico

pytestmark = pytest.mark.django_db


@pytest.fixture
def elementos_cargados():
    """Carga los 118 elementos para renderizar la vista de detalle."""
    call_command("cargar_elementos")


def _detalle_html(client, simbolo):
    elemento = ElementoQuimico.objects.get(simbolo_elemento=simbolo)
    respuesta = client.get(reverse("elemento_detalle", kwargs={"pk": elemento.pk}))
    assert respuesta.status_code == 200
    return respuesta.content.decode()


def test_detalle_muestra_radio_covalente_en_pm(client, elementos_cargados):
    html = _detalle_html(client, "Au")

    assert "Radio Covalente:" in html
    assert "136 pm" in html


def test_detalle_muestra_afinidad_con_clarificacion_delta_e(client, elementos_cargados):
    html = _detalle_html(client, "Cl")

    assert "Afinidad Electrónica:" in html
    assert "se liberan" in html
    assert "al captar un electrón" in html
    # abs() del valor almacenado (-348.60 -> 348.60), no el valor con signo.
    assert "-348" not in html.split("se liberan")[1].split("al captar")[0]


def test_detalle_muestra_nd_cuando_la_afinidad_es_none(client, elementos_cargados):
    html = _detalle_html(client, "He")

    assert "Afinidad Electrónica:" in html
    assert "N/D" in html


def test_detalle_muestra_peso_en_corchetes_sin_peso_estandar(client, elementos_cargados):
    html_polonio = _detalle_html(client, "Po")
    html_hidrogeno = _detalle_html(client, "H")

    assert "[209]" in html_polonio
    assert "1,0080" in html_hidrogeno
