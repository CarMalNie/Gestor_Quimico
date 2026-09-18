"""Tests for the cargar_elementos management command."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from app_quimico.data.elementos import ELEMENTOS_IUPAC_2021
from app_quimico.models import ElementoQuimico

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
