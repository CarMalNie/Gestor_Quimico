"""Form validation tests for CompuestoAplicacionForm and CompuestoQuimicoForm."""

import pytest

from app_quimico.forms import CompuestoAplicacionForm, CompuestoQuimicoForm
from app_quimico.models import Aplicacion, CompuestoQuimico, Industria


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


@pytest.mark.django_db
def test_compuesto_form_edicion_no_bloquea_formula():
    """Editing a saved compound must keep formula_compuesto editable (no readonly)."""
    industria = Industria.objects.get_or_create(nombre_industria="Farmacéutica")[0]
    compuesto = CompuestoQuimico.objects.create(
        nombre_compuesto="Agua",
        formula_compuesto="H2O",
        id_industria=industria,
    )

    form = CompuestoQuimicoForm(instance=compuesto)
    rendered = form["formula_compuesto"].as_widget()

    assert "readonly" not in rendered
    assert "bg-light" not in rendered
