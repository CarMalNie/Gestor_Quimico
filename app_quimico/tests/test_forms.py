"""Form validation tests for CompuestoAplicacionForm."""

import pytest

from app_quimico.forms import CompuestoAplicacionForm
from app_quimico.models import Aplicacion, Industria


@pytest.mark.django_db
def test_form_rechaza_industria_aplicacion_no_coincidente():
    industria_1 = Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]
    industria_2 = Industria.objects.create(nombre_industria="Alimentaria")
    aplicacion = Aplicacion.objects.create(id_industria=industria_2, nombre_uso="Disolvente")

    form = CompuestoAplicacionForm(data={
        "tipo_industria": industria_1.pk,
        "id_aplicacion": aplicacion.pk,
        "concentracion_minima": "10.00",
        "tipo_concentracion": "%p/p",
    })

    assert not form.is_valid()
    assert "no pertenece a la industria indicada" in str(form.errors)


@pytest.mark.django_db
def test_form_acepta_industria_aplicacion_coincidente():
    industria = Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]
    aplicacion = Aplicacion.objects.create(id_industria=industria, nombre_uso="Disolvente")

    form = CompuestoAplicacionForm(data={
        "tipo_industria": industria.pk,
        "id_aplicacion": aplicacion.pk,
        "concentracion_minima": "10.00",
        "tipo_concentracion": "%p/p",
    })

    assert form.is_valid()
