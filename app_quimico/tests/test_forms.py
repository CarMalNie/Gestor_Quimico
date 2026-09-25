"""Form validation tests for CompuestoAplicacionForm and CompuestoQuimicoForm."""

import pytest

from app_quimico.forms import (
    CATEGORIA_FILTRO_CHOICES,
    FILTRO_FAMILIA_METALES,
    FILTRO_FAMILIA_NO_METALES,
    CompuestoAplicacionForm,
    CompuestoQuimicoForm,
    ElementoFilterForm,
)
from app_quimico.models import (
    CATEGORIA_CHOICES,
    Aplicacion,
    CompuestoQuimico,
    Industria,
)


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


def test_filtro_categoria_incluye_familias_y_categorias_finas():
    """El select "Por Categoría" ofrece las 2 familias y las 10 finas."""
    campo = ElementoFilterForm().fields["categoria"]
    valores = [valor for valor, _ in campo.choices]

    assert valores[0] == ""
    assert valores[1] == FILTRO_FAMILIA_METALES
    assert valores[2] == FILTRO_FAMILIA_NO_METALES
    assert valores[3:] == [valor for valor, _ in CATEGORIA_CHOICES]
    assert len(valores) == 13


def test_filtro_categoria_no_colisiona_centinelas_con_categorias_reales():
    """Un valor centinela jamás puede ser un `categoria_elemento` real."""
    categorias_reales = {valor for valor, _ in CATEGORIA_CHOICES}

    assert FILTRO_FAMILIA_METALES not in categorias_reales
    assert FILTRO_FAMILIA_NO_METALES not in categorias_reales
    assert FILTRO_FAMILIA_METALES != FILTRO_FAMILIA_NO_METALES


def test_filtro_categoria_etiquetas_de_familia_son_bibliograficas():
    """Sin conteos ni agrupaciones inventadas: solo el término real."""
    etiquetas = dict(CATEGORIA_FILTRO_CHOICES)

    assert etiquetas[FILTRO_FAMILIA_METALES] == "Metales"
    assert etiquetas[FILTRO_FAMILIA_NO_METALES] == "No metales"
    assert not any(
        "Todos los" in etiqueta for _, etiqueta in CATEGORIA_FILTRO_CHOICES
    )


def test_categoria_choices_renombra_no_metales_a_otros_no_metales():
    """La categoría fina toma su nombre bibliográfico 'Otros No Metales'."""
    valores = [valor for valor, _ in CATEGORIA_CHOICES]

    assert "No Metales" not in valores
    assert "Otros No Metales" in valores
