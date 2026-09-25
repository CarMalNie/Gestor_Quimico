"""Tests for the view-mode toggle (vista=tarjetas|tabla) of ElementoListView."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from app_quimico.models import (
    CATEGORIA_CHOICES,
    FAMILIA_METALES,
    FAMILIA_NO_METALES,
    DetalleElemento,
    ElementoQuimico,
)

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


def test_leyenda_expone_dos_familias_y_diez_categorias_finas(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    leyenda = respuesta.context["leyenda"]
    familias = [chip for chip in leyenda if chip["tipo"] == "familia"]
    finas = [chip for chip in leyenda if chip["tipo"] == "fina"]

    assert len(familias) == 2
    assert len(finas) == 10
    # Las familias van primero, en este orden exacto.
    assert [chip["valor"] for chip in familias] == ["Metales", "No metales"]
    assert familias[0]["categorias"] == list(FAMILIA_METALES)
    assert familias[1]["categorias"] == list(FAMILIA_NO_METALES)
    assert [chip["valor"] for chip in finas] == [valor for valor, _ in CATEGORIA_CHOICES]


def test_familias_de_la_leyenda_cubren_los_conjuntos_esperados(
    client, elementos_cargados
):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    familias = {
        chip["valor"]: chip["categorias"]
        for chip in respuesta.context["leyenda"]
        if chip["tipo"] == "familia"
    }
    conteos = {
        categoria: DetalleElemento.objects.filter(
            categoria_elemento=categoria
        ).count()
        for categoria in FAMILIA_METALES + FAMILIA_NO_METALES
    }

    # 92 metales tras mover Po a "Otros Metales" (la auditoría citaba 91,
    # calculado cuando Po todavía era Metaloides); los 6 metaloides no cuentan
    # como metales. La familia no metálica reúne 20 elementos.
    assert sum(conteos[categoria] for categoria in familias["Metales"]) == 92
    assert sum(conteos[categoria] for categoria in familias["No metales"]) == 20


def test_leyenda_no_tiene_chips_muertos(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    leyenda = respuesta.context["leyenda"]
    categorias_en_uso = {
        detalle.categoria_elemento for detalle in DetalleElemento.objects.all()
    }

    assert leyenda
    for chip in leyenda:
        assert chip["valor"] != ""
        assert chip["categorias"], f"chip sin categorías: {chip}"
        # Ningún chip apunta a una categoría sin elementos en la base.
        assert set(chip["categorias"]) <= categorias_en_uso, chip


def test_posiciones_tabla_ubican_el_bloque_f_fuera_de_la_grilla_principal(
    client, elementos_cargados
):
    """Ce..Lu y Th..Lr se dibujan en filas despegadas; La/Ac quedan en (P6/P7, G3)."""
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    posiciones = respuesta.context["posiciones_tabla"]

    assert (posiciones["Ce"].fila, posiciones["Ce"].columna) == (9, 4)
    assert (posiciones["Lu"].fila, posiciones["Lu"].columna) == (9, 17)
    assert (posiciones["Th"].fila, posiciones["Th"].columna) == (10, 4)
    assert (posiciones["Lr"].fila, posiciones["Lr"].columna) == (10, 17)
    assert (posiciones["La"].fila, posiciones["La"].columna) == (6, 3)
    assert (posiciones["Ac"].fila, posiciones["Ac"].columna) == (7, 3)


def test_posiciones_tabla_respetan_la_grilla_principal(client, elementos_cargados):
    """Los elementos fuera del bloque f conservan (periodo, grupo) almacenados."""
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    posiciones = respuesta.context["posiciones_tabla"]

    assert (posiciones["H"].fila, posiciones["H"].columna) == (1, 1)
    assert (posiciones["He"].fila, posiciones["He"].columna) == (1, 18)
    assert (posiciones["Rf"].fila, posiciones["Rf"].columna) == (7, 4)
    assert (posiciones["Og"].fila, posiciones["Og"].columna) == (7, 18)


def test_posiciones_tabla_no_tienen_colisiones(client, elementos_cargados):
    """Cada uno de los 118 elementos ocupa una celda distinta de la grilla."""
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    posiciones = respuesta.context["posiciones_tabla"]
    celdas = {(posicion.fila, posicion.columna) for posicion in posiciones.values()}

    assert len(posiciones) == 118
    assert len(celdas) == 118


def test_posiciones_tabla_solo_existen_en_el_modo_tabla(client, elementos_cargados):
    """El modo tarjetas mantiene el contexto mínimo de siempre."""
    respuesta = client.get(reverse("elemento_lista"))

    assert respuesta.context["vista"] == "tarjetas"
    assert "posiciones_tabla" not in respuesta.context


def test_posiciones_tabla_tolera_elementos_sin_detalle(client):
    """Un elemento sin DetalleElemento no rompe la grilla (celda sin posicionar)."""
    ElementoQuimico.objects.create(
        numero_atomico_elemento=999,
        simbolo_elemento="Xx",
        nombre_elemento="Elemento sin detalle",
        peso_atomico_elemento=1,
    )

    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    assert respuesta.status_code == 200
    posicion = respuesta.context["posiciones_tabla"]["Xx"]
    assert (posicion.fila, posicion.columna) == (None, None)


def test_vista_tabla_renderiza_grilla_leyenda_y_filtros_del_cliente(
    client, elementos_cargados
):
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    html = respuesta.content.decode()

    assert 'id="pt-tabla"' in html
    assert 'style="grid-column: 4; grid-row: 9;"' in html  # Ce en la fila despegada
    assert "pt-sintetico" in html  # hook de honestidad para Z >= 104
    assert 'id="pt-buscar"' in html
    assert 'id="pt-peso-min"' in html
    assert html.count('class="pt-chip') == 12
    assert html.count('class="pt-chip pt-chip-familia') == 2
    assert (
        'data-categorias="Alcalinos|Alcalinos-térreos|Metales de Transición|'
        'Otros Metales|Lantánidos|Actínidos"'
    ) in html
    assert 'data-categorias="No Metales|Halógenos|Gases Nobles"' in html
    assert 'data-categoria="Lantánidos"' in html
    # Sin formulario del servidor en modo tabla (los filtros son del cliente).
    assert 'name="busqueda_nombre"' not in html
    assert '?vista=tarjetas' in html and '?vista=tabla' in html


def test_vista_tarjetas_mantiene_el_formulario_del_servidor(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"))

    html = respuesta.content.decode()

    assert 'name="busqueda_nombre"' in html
    assert 'id="pt-tabla"' not in html
    assert 'id="pt-buscar"' not in html
    assert '?vista=tarjetas' in html and '?vista=tabla' in html


def test_vista_tabla_no_filtra_comentarios_multilinea_al_html(
    client, elementos_cargados
):
    """Django {# #} comenta una sola linea: el bloque multilinea no debe renderizarse."""
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})

    html = respuesta.content.decode()

    assert "Grilla peri\u00f3dica: 18 columnas" not in html
    assert "posiciones_tabla" not in html


def test_encabezado_compartido_usa_el_titulo_corto_en_ambas_vistas(
    client, elementos_cargados
):
    titulo = "<h1>\u269b\ufe0f Tabla Peri\u00f3dica</h1>"

    tabla = client.get(reverse("elemento_lista"), {"vista": "tabla"})
    tarjetas = client.get(reverse("elemento_lista"))

    assert titulo in tabla.content.decode()
    assert titulo in tarjetas.content.decode()
