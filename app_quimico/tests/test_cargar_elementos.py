"""Tests for the cargar_elementos management command."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from app_quimico.data.elementos import ELEMENTOS_IUPAC_2021
from app_quimico.models import DetalleElemento, ElementoQuimico

pytestmark = pytest.mark.django_db


def test_cargar_elementos_crea_los_118():
    call_command("cargar_elementos")
    assert ElementoQuimico.objects.count() == 118

    hidrogeno = ElementoQuimico.objects.get(simbolo_elemento="H")
    assert hidrogeno.nombre_elemento == "Hidrógeno"
    assert hidrogeno.numero_atomico_elemento == 1
    assert hidrogeno.peso_atomico_elemento == Decimal("1.0080")

    oganesson = ElementoQuimico.objects.get(simbolo_elemento="Og")
    assert oganesson.numero_atomico_elemento == 118
    assert oganesson.peso_atomico_elemento == Decimal("294.0000")


def test_cargar_elementos_es_idempotente():
    call_command("cargar_elementos")
    call_command("cargar_elementos")

    assert ElementoQuimico.objects.count() == 118


def test_cargar_elementos_crea_los_118_detalles():
    call_command("cargar_elementos")

    assert ElementoQuimico.objects.count() == 118
    assert DetalleElemento.objects.count() == 118


def test_cargar_elementos_detalles_spot_checks():
    call_command("cargar_elementos")

    hidrogeno = DetalleElemento.objects.get(id_elemento__simbolo_elemento="H")
    assert hidrogeno.grupo_elemento == 1
    assert hidrogeno.periodo_elemento == 1
    assert hidrogeno.categoria_elemento == "No Metales"
    assert hidrogeno.electronegatividad == Decimal("2.20")
    assert hidrogeno.afinidad_electronica == Decimal("-72.80")
    assert hidrogeno.energia_de_ionizacion == Decimal("1312.00")
    assert hidrogeno.radio_covalente == Decimal("0.370")

    cloro = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Cl")
    assert cloro.afinidad_electronica == Decimal("-348.60")
    assert cloro.energia_de_ionizacion == Decimal("1251.20")

    cesio = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Cs")
    assert cesio.energia_de_ionizacion == Decimal("375.70")

    oganesson = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Og")
    assert oganesson.electronegatividad is None
    assert oganesson.afinidad_electronica is None
    assert oganesson.energia_de_ionizacion is None
    assert oganesson.radio_covalente is None
    assert oganesson.descripcion_elemento

    cerio = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Ce")
    assert cerio.categoria_elemento == "Lantánidos"
    assert cerio.grupo_elemento == 3


def test_cargar_elementos_detalles_es_idempotente():
    call_command("cargar_elementos")
    call_command("cargar_elementos")

    assert ElementoQuimico.objects.count() == 118
    assert DetalleElemento.objects.count() == 118


def test_cargar_elementos_detalles_dentro_de_limites_de_validadores():
    call_command("cargar_elementos")
    assert DetalleElemento.objects.count() == 118

    for detalle in DetalleElemento.objects.all():
        if detalle.electronegatividad is not None:
            assert Decimal("0.70") <= detalle.electronegatividad <= Decimal("4.00")
        if detalle.afinidad_electronica is not None:
            assert (
                Decimal("-348.60")
                <= detalle.afinidad_electronica
                <= Decimal("-0.0001")
            )
        if detalle.energia_de_ionizacion is not None:
            assert (
                Decimal("375.70")
                <= detalle.energia_de_ionizacion
                <= Decimal("2372.30")
            )
        if detalle.radio_covalente is not None:
            assert Decimal("0.32") <= detalle.radio_covalente <= Decimal("2.98")


def test_cargar_elementos_clasifica_polonio_como_otro_metal():
    """Po es post-transición/Otros Metales por consenso moderno (RSC, Wikipedia)."""
    call_command("cargar_elementos")

    polonio = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Po")

    assert polonio.categoria_elemento == "Otros Metales"


def test_cargar_elementos_superpesados_incluyen_nota_de_prediccion():
    """Z >= 104: la descripción advierte que las propiedades son predicciones."""
    call_command("cargar_elementos")

    for numero in range(104, 119):
        detalle = DetalleElemento.objects.get(
            id_elemento__numero_atomico_elemento=numero
        )
        assert "predicciones" in detalle.descripcion_elemento.lower(), detalle

