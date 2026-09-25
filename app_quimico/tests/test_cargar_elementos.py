"""Tests for the cargar_elementos management command."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from app_quimico.data.elementos import ELEMENTOS_IUPAC_2021
from app_quimico.models import (
    ELEMENTOS_SIN_PESO_ESTANDAR,
    DetalleElemento,
    ElementoQuimico,
)

pytestmark = pytest.mark.django_db


def test_cargar_elementos_crea_los_118():
    call_command("cargar_elementos")
    assert ElementoQuimico.objects.count() == 118

    hidrogeno = ElementoQuimico.objects.get(simbolo_elemento="H")
    assert hidrogeno.nombre_elemento == "Hidrógeno"
    assert hidrogeno.numero_atomico_elemento == 1
    assert hidrogeno.peso_atomico_elemento == Decimal("1.0080")

    # CIAAW 2024 revisó el peso del circonio a 91.222 (5 cifras significativas).
    circonio = ElementoQuimico.objects.get(simbolo_elemento="Zr")
    assert circonio.peso_atomico_elemento == Decimal("91.2220")

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
    assert hidrogeno.categoria_elemento == "Otros No Metales"
    assert hidrogeno.electronegatividad == Decimal("2.20")
    assert hidrogeno.afinidad_electronica == Decimal("-72.80")
    assert hidrogeno.energia_de_ionizacion == Decimal("1312.00")
    assert hidrogeno.radio_covalente == Decimal("31")

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


def test_cargar_elementos_usa_el_nombre_bibliografico_otros_no_metales():
    """La categoría fina 'No Metales' pasa a 'Otros No Metales'.

    'Otros No Metales' es el nombre estándar en la bibliografía (y el rótulo
    original de la cátedra); así deja de chocar con la familia 'No metales'.
    Exactamente 7 elementos la usan: H, C, N, O, P, S y Se.
    """
    call_command("cargar_elementos")

    assert (
        DetalleElemento.objects.filter(categoria_elemento="No Metales").count()
        == 0
    )
    otros_no_metales = DetalleElemento.objects.filter(
        categoria_elemento="Otros No Metales"
    ).order_by("id_elemento__numero_atomico_elemento")

    assert otros_no_metales.count() == 7
    assert [
        detalle.id_elemento.simbolo_elemento for detalle in otros_no_metales
    ] == ["H", "C", "N", "O", "P", "S", "Se"]


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
            assert Decimal("28") <= detalle.radio_covalente <= Decimal("350")


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


# Radios covalentes de Cordero et al. 2008 (pm): spot-checks del dataset.
RADIOS_CORDERO_ESPERADOS = {"H": "31", "Cs": "244", "Au": "136"}

# Afinidades electrónicas medidas (ΔE negativo) que estaban en NULL.
AFINIDADES_MEDIDAS_NUEVAS = {
    "Sr": "-5.00",
    "Ba": "-14.00",
    "Hf": "-17.00",
    "La": "-54.00",
    "Ce": "-58.00",
    "Pr": "-11.00",
    "Nd": "-9.00",
    "Pm": "-12.00",
    "Sm": "-16.00",
    "Eu": "-11.00",
    "Gd": "-21.00",
    "Tb": "-13.00",
    "Dy": "-1.00",
    "Ho": "-33.00",
    "Er": "-30.00",
    "Tm": "-99.00",
    "Lu": "-23.00",
    "Re": "-6.00",
    "Os": "-104.00",
    "Ir": "-151.00",
    "Pt": "-205.00",
}

# Afinidades en disputa entre tablas publicadas: se dejan como están.
AFINIDADES_EN_DISPUTA = {
    "Mo": "-92.00",
    "In": "-29.00",
    "Tl": "-19.00",
    "Po": "-183.00",
    "At": "-270.00",
}


def test_cargar_elementos_radios_covalentes_cordero_2008_en_pm():
    call_command("cargar_elementos")

    for simbolo, valor in RADIOS_CORDERO_ESPERADOS.items():
        detalle = DetalleElemento.objects.get(id_elemento__simbolo_elemento=simbolo)
        assert detalle.radio_covalente == Decimal(valor), simbolo


def test_cargar_elementos_solo_cordero_2008_tiene_radios():
    """Los 95 elementos de Cordero 2008 tienen radio; He/Bk/Cf y Z>=104 no."""
    call_command("cargar_elementos")

    con_radio = {
        detalle.id_elemento.simbolo_elemento
        for detalle in DetalleElemento.objects.exclude(radio_covalente=None)
    }

    assert len(con_radio) == 95
    assert {"He", "Bk", "Cf"}.isdisjoint(con_radio)


def test_cargar_elementos_afinidades_medidas_rellenadas():
    call_command("cargar_elementos")

    for simbolo, valor in AFINIDADES_MEDIDAS_NUEVAS.items():
        detalle = DetalleElemento.objects.get(id_elemento__simbolo_elemento=simbolo)
        assert detalle.afinidad_electronica == Decimal(valor), simbolo


def test_cargar_elementos_afinidades_en_disputa_sin_cambios():
    call_command("cargar_elementos")

    for simbolo, valor in AFINIDADES_EN_DISPUTA.items():
        detalle = DetalleElemento.objects.get(id_elemento__simbolo_elemento=simbolo)
        assert detalle.afinidad_electronica == Decimal(valor), simbolo


def test_cargar_elementos_correcciones_de_en_e_ionizacion():
    call_command("cargar_elementos")

    americio = DetalleElemento.objects.get(id_elemento__simbolo_elemento="Am")
    assert americio.electronegatividad == Decimal("1.30")

    esperados = {"Tc": "686.90", "At": "899.00", "No": "639.00"}
    for simbolo, valor in esperados.items():
        detalle = DetalleElemento.objects.get(id_elemento__simbolo_elemento=simbolo)
        assert detalle.energia_de_ionizacion == Decimal(valor), simbolo


def test_peso_atomico_para_mostrar_usa_corchetes_sin_peso_estandar():
    call_command("cargar_elementos")

    polonio = ElementoQuimico.objects.get(simbolo_elemento="Po")
    hidrogeno = ElementoQuimico.objects.get(simbolo_elemento="H")

    assert polonio.peso_atomico_para_mostrar == "[209]"
    assert polonio.peso_atomico_es_masico is True
    assert hidrogeno.peso_atomico_para_mostrar == Decimal("1.0080")
    assert hidrogeno.peso_atomico_es_masico is False


def test_peso_atomico_para_mostrar_cubre_los_34_sin_peso_estandar():
    call_command("cargar_elementos")

    con_corchetes = {
        elemento.simbolo_elemento
        for elemento in ElementoQuimico.objects.all()
        if elemento.peso_atomico_es_masico
    }

    assert con_corchetes == set(ELEMENTOS_SIN_PESO_ESTANDAR)
    assert len(con_corchetes) == 34

