"""Tests for the view-mode toggle (vista=tarjetas|tabla) of ElementoListView."""

import re
from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils.text import slugify

from app_quimico.models import (
    CATEGORIA_CHOICES,
    FAMILIA_METALES,
    FAMILIA_NO_METALES,
    DetalleElemento,
    ElementoQuimico,
)

pytestmark = pytest.mark.django_db

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERIODIC_TABLE_CSS = PROJECT_ROOT / "static" / "css" / "periodic_table.css"
PERIODIC_TABLE_JS = PROJECT_ROOT / "static" / "js" / "periodic_table.js"
PERIODIC_TABLE_TEMPLATE = (
    PROJECT_ROOT
    / "app_quimico"
    / "templates"
    / "app_quimico"
    / "elemento_quimico"
    / "elemento_lista.html"
)
ELEMENTO_DETALLE_TEMPLATE = (
    PROJECT_ROOT
    / "app_quimico"
    / "templates"
    / "app_quimico"
    / "elemento_quimico"
    / "elemento_detalle.html"
)


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
    assert [chip["valor"] for chip in familias] == [
        "Metales",
        "No metales",
    ]
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
    # Ce en la fila despegada conserva su posición y suma la variable de la
    # entrada escalonada (--pt-z).
    assert 'style="grid-column: 4; grid-row: 9; --pt-z: 58;"' in html
    assert "pt-sintetico" in html  # hook de honestidad para Z >= 104
    assert 'id="pt-buscar"' in html
    assert 'id="pt-peso-min"' in html
    assert html.count('class="pt-chip') == 12
    assert html.count('class="pt-chip pt-chip-familia') == 2
    assert (
        'data-categorias="Alcalinos|Alcalinos-térreos|Metales de Transición|'
        'Otros Metales|Lantánidos|Actínidos"'
    ) in html
    assert 'data-categorias="Otros No Metales|Halógenos|Gases Nobles"' in html
    assert 'data-categoria="Lantánidos"' in html
    # Sin formulario del servidor en modo tabla (los filtros son del cliente).
    assert 'name="busqueda_nombre"' not in html
    assert '?vista=tarjetas' in html and '?vista=tabla' in html


def test_leyenda_usa_terminologia_bibliografica_sin_inventar_agrupaciones(
    client, elementos_cargados
):
    """Las familias se llaman 'Metales'/'No metales': conceptos reales.

    El operador rechazó el rótulo "Todos los...". La categoría fina se llama
    'Otros No Metales' (nombre bibliográfico), así que el slug de la familia
    'No metales' (`pt-chip-no-metales`) ya no choca con ella."""
    respuesta = client.get(reverse("elemento_lista"), {"vista": "tabla"})
    html = respuesta.content.decode()

    assert "pt-chip-familia" in html
    # Etiquetas de familia bibliográficas y únicas en la leyenda.
    assert html.count(">Metales<") == 1
    assert html.count(">No metales<") == 1
    # La categoría fina renombrada conserva su propia etiqueta.
    assert html.count(">Otros No Metales<") == 1
    # Sin la agrupación inventada en ninguna parte de la leyenda.
    assert ">Todos los" not in html
    # Slugs sin colisión: familia metales / familia no-metales / fina
    # otros-no-metales.
    assert (
        'class="pt-chip pt-chip-familia pt-chip-metales"'
        ' data-categorias="Alcalinos|'
    ) in html
    assert (
        'class="pt-chip pt-chip-familia pt-chip-no-metales"'
        ' data-categorias="Otros No Metales|'
    ) in html
    assert (
        'class="pt-chip pt-chip-otros-no-metales"'
        ' data-categoria="Otros No Metales"'
    ) in html


def test_form_de_filtros_de_tarjetas_expone_familias_y_categorias_finas(
    client, elementos_cargados
):
    respuesta = client.get(reverse("elemento_lista"))

    campo = respuesta.context["filter_form"].fields["categoria"]
    valores = [valor for valor, _ in campo.choices]
    etiquetas = dict(campo.choices)

    assert valores[0] == ""
    assert valores[1:3] == ["familia_metales", "familia_no_metales"]
    assert valores[3:] == [valor for valor, _ in CATEGORIA_CHOICES]
    assert etiquetas["familia_metales"] == "Metales"
    assert etiquetas["familia_no_metales"] == "No metales"


def test_tarjetas_filtran_por_familia_metales(client, elementos_cargados):
    respuesta = client.get(
        reverse("elemento_lista"), {"categoria": "familia_metales"}
    )

    assert respuesta.status_code == 200
    elementos = list(respuesta.context["elementos"])
    assert len(elementos) == 92
    assert all(
        elemento.detalleelemento.categoria_elemento in FAMILIA_METALES
        for elemento in elementos
    )
    # Los metaloides no cuentan como metales.
    simbolos = {elemento.simbolo_elemento for elemento in elementos}
    assert "B" not in simbolos
    assert "Si" not in simbolos


def test_tarjetas_filtran_por_familia_no_metales(client, elementos_cargados):
    respuesta = client.get(
        reverse("elemento_lista"), {"categoria": "familia_no_metales"}
    )

    assert respuesta.status_code == 200
    elementos = list(respuesta.context["elementos"])
    assert len(elementos) == 20
    assert all(
        elemento.detalleelemento.categoria_elemento in FAMILIA_NO_METALES
        for elemento in elementos
    )


def test_tarjetas_mantienen_exacta_la_categoria_fina(client, elementos_cargados):
    respuesta = client.get(reverse("elemento_lista"), {"categoria": "Alcalinos"})

    elementos = list(respuesta.context["elementos"])
    assert len(elementos) == 6
    assert all(
        elemento.detalleelemento.categoria_elemento == "Alcalinos"
        for elemento in elementos
    )


def test_tarjetas_ignoran_un_centinela_de_familia_desconocido(
    client, elementos_cargados
):
    """Un valor inventado no debe filtrar como si fuera una categoría real."""
    respuesta = client.get(
        reverse("elemento_lista"), {"categoria": "familia_inexistente"}
    )

    assert respuesta.status_code == 200
    assert len(list(respuesta.context["elementos"])) == 118


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


def test_ningun_comentario_django_se_filtraba_al_html(
    client, elementos_cargados
):
    """Anti-regresión general del leak {# #}: django template comments que
    abarcan más de una línea (o cuyo cierre queda tras un salto de línea)

    se renderizan como texto. Regresión T2 E2: el script inline tenía su

    {# #} en 3 líneas y el comentario aparecía sobre la vista. La aserción
    es genérica (no tokenizada a un texto): ningún fragmento con la sintaxis
    "{#" ni "#}" debe sobrevivir al render en ninguna de las dos vistas."""
    for query, vista in (({}, "tarjetas"), ({"vista": "tabla"}, "tabla")):
        respuesta = client.get(reverse("elemento_lista"), query)
        html = respuesta.content.decode()
        assert "{#" not in html, f"comentario filtrado en vista {vista}"
        assert "#}" not in html, f"cierre de comentario filtrado en vista {vista}"


def test_encabezado_compartido_usa_el_titulo_corto_en_ambas_vistas(
    client, elementos_cargados
):
    titulo = "<h1>\u269b\ufe0f Tabla Peri\u00f3dica</h1>"

    tabla = client.get(reverse("elemento_lista"), {"vista": "tabla"})
    tarjetas = client.get(reverse("elemento_lista"))

    assert titulo in tabla.content.decode()
    assert titulo in tarjetas.content.decode()


def test_tarjetas_muestran_peso_en_corchetes_sin_peso_estandar(
    client, elementos_cargados
):
    """Po (sin peso estándar CIAAW) va entre corchetes; H muestra el valor plano."""
    html = client.get(reverse("elemento_lista")).content.decode()

    assert "[209]" in html  # Po, masa del isótopo representativo
    assert "1,0080" in html  # H, peso estándar sin corchetes


def test_grilla_periodica_mantiene_data_peso_numerico(client, elementos_cargados):
    """La celda de la grilla no debe llevar corchetes en data-peso."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    assert 'data-peso="209.0000"' in html
    assert 'data-peso="[209]"' not in html


# ========================================================================= #
# Estilos de la leyenda (CSS) y cache-busting
# ========================================================================= #


def test_periodic_table_css_cache_bust_was_bumped():
    """La entrada escalonada agregó reglas a la hoja: el ?v del CSS sube."""
    source = PERIODIC_TABLE_TEMPLATE.read_text(encoding="utf-8")

    assert "css/periodic_table.css' %}?v=7" in source


def _paleta_declarada_para_chip(css, slug):
    """Variables de paleta (--pt-*) usadas por la regla `.pt-chip-<slug>`."""
    propio = f".pt-chip-{slug}"
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    variables = set()
    for selector, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", sin_comentarios):
        if propio in {parte.strip() for parte in selector.split(",")}:
            variables.update(re.findall(r"var\(\s*(--pt-[\w-]+)", cuerpo))
    return variables


def test_css_estiliza_los_slugs_de_chip_usados_en_ambos_temas(
    client, elementos_cargados
):
    """Cada chip de la leyenda tiene su regla y su paleta en claro y oscuro."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    css_sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    leyenda = client.get(
        reverse("elemento_lista"), {"vista": "tabla"}
    ).context["leyenda"]
    slugs = {slugify(chip["valor"]) for chip in leyenda}

    assert len(slugs) == 12
    for slug in slugs:
        variables = _paleta_declarada_para_chip(css, slug)
        assert variables, f"sin regla CSS para .pt-chip-{slug}"
        for variable in variables:
            # Cada variable de tema se declara una vez por tema (claro/oscuro).
            assert css_sin_comentarios.count(f"{variable}:") == 2, (
                f"{variable} no está definida en ambos temas"
            )


def test_css_no_conserva_clases_de_agrupaciones_inventadas():
    """Los slugs 'todos-los-*' quedaron muertos tras el renombre de T11."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")

    assert "pt-chip-todos-los-metales" not in css
    assert "pt-chip-todos-los-no-metales" not in css
    assert "Todos los" not in css


def test_css_no_conserva_celdas_de_familia():
    """Las familias solo son chips: nunca se dibujan como celdas de la grilla.

    '.pt-celda-metales' y '.pt-celda-no-metales' quedaron muertos al poner los
    chips de familia (views.py solo emite chips para ellas) y se removieron.
    """
    css_sin_comentarios = re.sub(
        r"/\*.*?\*/", "", PERIODIC_TABLE_CSS.read_text(encoding="utf-8"), flags=re.S
    )

    # Límite de token: '.pt-celda-metales' no es 'pt-celda-metales-de-transicion'.
    for muerto in ("pt-celda-metales", "pt-celda-no-metales"):
        assert not re.search(rf"\.{re.escape(muerto)}(?![\w-])", css_sin_comentarios)
    # Los chips de familia sí siguen estilizados (reusan la paleta fina).
    assert ".pt-chip-metales" in css_sin_comentarios
    assert ".pt-chip-no-metales" in css_sin_comentarios


def test_ningun_celda_lleva_slug_de_familia(client, elementos_cargados):
    """La grilla renderizada nunca emite clases pt-celda-<familia>."""
    response = client.get(reverse("elemento_lista"), {"vista": "tabla"})
    html = response.content.decode()

    slugs_familia = {slugify(f) for f in ("Metales", "No metales")}
    for slug in slugs_familia:
        # Límite de token: 'pt-celda-metales' no es substring de
        # 'pt-celda-metales-de-transicion' ni de la clase de otros slugs.
        assert not re.search(rf"pt-celda-{re.escape(slug)}(?![\w-])", html)


# ========================================================================= #
# Preferencia de vista recordada en el cliente (localStorage)
# ========================================================================= #


def test_periodic_table_js_cache_bust_was_bumped():
    """El JS sumó la entrada escalonada: el ?v sube para invalidar caché."""
    source = PERIODIC_TABLE_TEMPLATE.read_text(encoding="utf-8")

    assert "js/periodic_table.js' %}?v=8" in source


def test_js_de_la_tabla_persiste_la_vista_del_selector():
    """El JS guarda en localStorage la vista elegida al tocar el selector.

    La preferencia se escribe solo por click explícito, reconociendo el enlace
    por su href (?vista=...); la navegación no se frena (sin preventDefault).
    """
    source = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert "gestorQuimicoVistaElementos" in source
    assert 'indexOf("vista=")' in source
    assert "localStorage.setItem" in source
    assert 'addEventListener("click"' in source
    assert '"tarjetas"' in source and '"tabla"' in source
    # La navegación del enlace sigue su curso: el handler del selector no
    # cancela el evento. La aserción se acota a esa función porque la
    # navegación por flechas de T4 sí usa preventDefault (evita el scroll).
    assert ".preventDefault(" not in _cuerpo_de_funcion(source, "initPreferenciaVista")


def test_selector_de_vista_mantiene_enlaces_explicitos(client, elementos_cargados):
    """Los dos botones del selector siguen navegando con ?vista= explícito."""
    html = client.get(reverse("elemento_lista")).content.decode()

    assert 'href="?vista=tarjetas"' in html
    assert 'href="?vista=tabla"' in html


def test_lista_recupera_la_vista_guardada_en_el_cliente(client, elementos_cargados):
    """El script inline redirige a ?vista=tabla solo bajo las tres condiciones.

    (1) la URL no trae `vista`, (2) lo guardado es exactamente 'tabla' y
    (3) el servidor renderizó la vista 'tarjetas' (data-vista-actual). Tras la
    redirección la URL lleva ?vista=tabla, así que el guard no puede repetirse.
    """
    html = client.get(reverse("elemento_lista")).content.decode()

    # Clave de almacenamiento compartida con el JS del selector.
    assert "gestorQuimicoVistaElementos" in html
    # Condición 3: el template expone la vista servida en el grupo de botones.
    assert 'data-vista-actual="tarjetas"' in html
    assert '=== "tarjetas"' in html
    # Condición 1: sin parámetro vista en la query; condición 2: valor 'tabla'.
    assert "location.search" in html
    assert '=== "tabla"' in html
    # Redirección sin apilar historial (reemplaza la entrada actual).
    assert 'location.replace("?vista=tabla")' in html


def test_lista_en_vista_tabla_no_redirige(client, elementos_cargados):
    """En la vista tabla el atributo vale 'tabla': la tercera condición falla y
    el guard no puede repetir la redirección (sin loop)."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    assert 'data-vista-actual="tabla"' in html
    assert 'data-vista-actual="tarjetas"' not in html


def test_detalle_mantiene_enlace_plano_al_listado(client, elementos_cargados):
    """El botón 'Volver al Listado' queda sin ?vista: la preferencia la
    resuelve el script inline de la lista."""
    elemento = ElementoQuimico.objects.first()
    html = client.get(
        reverse("elemento_detalle", kwargs={"pk": elemento.pk})
    ).content.decode()

    assert re.search(
        r'href="[^"]*"\s+class="btn btn-secondary mt-4">Volver al Listado', html
    )
    assert "?vista=" not in html


# ========================================================================= #
# Tarjeta de detalle al hover/focus (T3 de p1-periodic-table-e2)
# ========================================================================= #


def _celda_de_simbolo(html, simbolo):
    """Devuelve la etiqueta <a> de la celda del símbolo (sin su contenido)."""
    for etiqueta in re.findall(r"<a\b[^>]*>", html):
        if f'data-simbolo="{simbolo.lower()}"' in etiqueta:
            return etiqueta
    raise AssertionError(f"celda no encontrada: {simbolo}")


def test_card_de_detalle_existe_solo_en_la_vista_tabla(client, elementos_cargados):
    """Una única card flotante renderizada junto a la grilla (nunca en tarjetas)."""
    html_tabla = client.get(
        reverse("elemento_lista"), {"vista": "tabla"}
    ).content.decode()
    html_tarjetas = client.get(reverse("elemento_lista")).content.decode()

    assert 'id="pt-card"' in html_tabla
    assert 'class="pt-card"' in html_tabla
    assert 'role="tooltip"' in html_tabla
    # Arranca oculta y decorativa (el JS administra aria-hidden).
    assert 'aria-hidden="true"' in html_tabla
    assert html_tabla.count('id="pt-card"') == 1
    # La vista de tarjetas conserva el contexto mínimo de siempre.
    assert 'id="pt-card"' not in html_tarjetas


def test_celdas_exponen_grupo_y_periodo_para_la_card(client, elementos_cargados):
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    hidrogeno = _celda_de_simbolo(html, "H")
    assert 'data-grupo="1"' in hidrogeno
    assert 'data-periodo="1"' in hidrogeno

    polonio = _celda_de_simbolo(html, "Po")
    assert 'data-grupo="16"' in polonio
    assert 'data-periodo="6"' in polonio


def test_celdas_distinguen_peso_atomico_de_numero_masico(client, elementos_cargados):
    """La card no puede rotular '[209]' como peso atómico: es número másico."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    polonio = _celda_de_simbolo(html, "Po")
    assert 'data-peso-masico="1"' in polonio
    assert 'data-peso-mostrar="[209]"' in polonio

    hidrogeno = _celda_de_simbolo(html, "H")
    assert 'data-peso-masico="0"' in hidrogeno
    # Localización es-cl: coma decimal en el peso mostrable (mismo formato
    # que la vista de tarjetas); data-peso sigue siendo el valor numérico
    # plano (punto) para el filtro min_peso_atomico del cliente.
    assert 'data-peso-mostrar="1,0080"' in hidrogeno


def test_celda_sin_detalle_no_emite_grupo_ni_periodo(client):
    """Sin DetalleElemento la celda se renderiza, pero sin data-grupo/periodo."""
    ElementoQuimico.objects.create(
        numero_atomico_elemento=999,
        simbolo_elemento="Xx",
        nombre_elemento="Elemento sin detalle",
        peso_atomico_elemento=1,
    )
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    celda = _celda_de_simbolo(html, "Xx")
    assert "data-grupo" not in celda
    assert "data-periodo" not in celda


def test_css_define_la_card_flotante_sin_capturar_el_puntero():
    """La card es flotante y deja pasar el mouse: nunca realimenta el hover."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    assert ".pt-card" in sin_comentarios
    assert "pointer-events: none" in sin_comentarios
    assert "max-width: 240px" in sin_comentarios


def test_css_de_la_card_sigue_el_tema_activo():
    """La card usa variables de Bootstrap: cambia con [data-bs-theme]."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    bloque = re.search(r"\.pt-card\s*\{([^}]*)\}", sin_comentarios)
    assert bloque, "sin regla .pt-card"
    cuerpo = bloque.group(1)
    assert "var(--bs-body-bg)" in cuerpo
    assert "var(--bs-body-color)" in cuerpo


def test_css_de_la_card_respeta_prefers_reduced_motion():
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    reducido = re.search(
        r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([^@]*)\}",
        sin_comentarios,
        flags=re.S,
    )
    assert reducido, "sin bloque prefers-reduced-motion"
    assert ".pt-card" in reducido.group(1)
    assert "transition: none" in reducido.group(1)


def test_js_de_la_card_lee_los_datos_de_la_celda():
    source = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert "initDetailCard" in source
    for atributo in (
        "data-simbolo",
        "data-nombre",
        "data-categoria",
        "data-grupo",
        "data-periodo",
        "data-peso-mostrar",
        "data-peso-masico",
    ):
        assert atributo in source, f"el JS no lee {atributo}"


def test_js_de_la_card_se_inicializa_desde_el_dispatch(client, elementos_cargados):
    source = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    # Se registra en el init combinado, junto a la preferencia y la tabla.
    assert re.search(
        r"function init\(\)\s*\{[^}]*initDetailCard\(\)", source, flags=re.S
    )
    # Solo actúa si existen la grilla y la card.
    assert 'getElementById("pt-tabla")' in source
    assert 'getElementById("pt-card")' in source


def test_js_de_la_card_oculta_con_mouse_focus_escape_y_scroll():
    source = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert '"mouseover"' in source and '"mouseout"' in source
    assert '"focusin"' in source and '"focusout"' in source
    assert '"Escape"' in source
    assert '"scroll"' in source
    assert 'setAttribute("aria-hidden"' in source
    # Touch: no se activa en dispositivos sin hover real.
    assert "(hover: none)" in source


def test_js_de_la_card_usa_rotulos_neutrales_y_honestos():
    source = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    # Sin texto accionable: la celda entera es el enlace; un "Ver detalle"
    # dentro de la card invitaba a un clic que no existía (feedback del
    # operador). Sin rótulo de acción, solo datos.
    assert "Ver detalle" not in source
    assert "Categoría" in source
    assert "Grupo/Período" in source
    assert "Peso atómico" in source
    assert "Número másico" in source


# ========================================================================= #
# Navegación por teclado y ARIA (T4 de p1-periodic-table-e2)
# ========================================================================= #


def _cuerpo_de_funcion(fuente, nombre):
    """Cuerpo de `function <nombre>(...) { ... }` con llaves balanceadas."""
    inicio = fuente.index(f"function {nombre}(")
    llave = fuente.index("{", inicio)
    profundidad = 0
    for indice in range(llave, len(fuente)):
        if fuente[indice] == "{":
            profundidad += 1
        elif fuente[indice] == "}":
            profundidad -= 1
            if profundidad == 0:
                return fuente[llave : indice + 1]
    raise AssertionError(f"función sin cierre: {nombre}")


def _contenedor_pt_tabla(html):
    """Etiqueta de apertura del contenedor de la grilla."""
    coincidencia = re.search(r'<div\b[^>]*id="pt-tabla"[^>]*>', html)
    if not coincidencia:
        raise AssertionError("contenedor #pt-tabla no encontrado")
    return coincidencia.group(0)


def test_celdas_llevan_aria_label_descriptivo(client, elementos_cargados):
    """Cada celda describe símbolo, nombre, Z y categoría para lectores de pantalla."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    lantano = _celda_de_simbolo(html, "La")
    assert 'aria-label="La — Lantano, número atómico 57, Lantánidos"' in lantano
    # Sin peso: el nombre accesible es corto y el detalle completo vive en su
    # página (el peso ya está en la card). Casing canónico IUPAC en el label,
    # no el minúsculo que usan los data-* para el filtro del cliente.
    etiqueta = re.search(r'aria-label="([^"]*)"', lantano).group(1)
    assert "g/mol" not in etiqueta
    assert "Lantano" in etiqueta and "lantano" not in etiqueta

    # La grilla completa lo lleva: no es una celda de muestra.
    assert "aria-label=" in _celda_de_simbolo(html, "H")
    assert "número atómico 84" in _celda_de_simbolo(html, "Po")


def test_aria_label_empieza_con_el_simbolo_visible(client, elementos_cargados):
    """WCAG 2.5.3: el texto visible (símbolo canónico) encabeza el nombre accesible."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    for simbolo in ("H", "La", "Po"):
        celda = _celda_de_simbolo(html, simbolo)
        assert f'aria-label="{simbolo} — ' in celda


def test_celda_sin_detalle_no_incluye_categoria_en_el_aria_label(client):
    """Sin DetalleElemento el nombre accesible omite el tramo de categoría."""
    ElementoQuimico.objects.create(
        numero_atomico_elemento=999,
        simbolo_elemento="Xx",
        nombre_elemento="Elemento sin detalle",
        peso_atomico_elemento=1,
    )
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    celda = _celda_de_simbolo(html, "Xx")
    assert 'aria-label="Xx — Elemento sin detalle, número atómico 999"' in celda
    assert "None" not in celda


def test_tabla_declara_su_proposito_en_el_contenedor(client, elementos_cargados):
    """El contenedor anuncia qué es la grilla; las celdas siguen siendo <a>."""
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    contenedor = _contenedor_pt_tabla(html)
    assert (
        'aria-label="Tabla periódica interactiva: 118 elementos químicos"'
        in contenedor
    )
    # Sin roles de widget: son 118 enlaces en orden de lectura.
    assert 'role="grid"' not in html


def test_js_de_la_navegacion_expone_la_roving_tabindex_y_las_flechas():
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "initNavegacionTeclado")

    assert "setRoving" in cuerpo
    # Una sola celda alcanzable con Tab: 0 en la roving, -1 en el resto.
    assert 'setAttribute("tabindex", "0")' in cuerpo
    assert 'setAttribute("tabindex", "-1")' in cuerpo
    for tecla in ("ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Home", "End"):
        assert f'"{tecla}"' in cuerpo, f"sin manejo de {tecla}"
    # La coordenada sale del style inline de la plantilla.
    assert "grid-column" in cuerpo and "grid-row" in cuerpo
    # Las flechas mueven el foco y no scrollean la grilla.
    assert ".focus()" in cuerpo
    assert ".preventDefault(" in cuerpo


def test_js_de_la_navegacion_no_depende_del_media_hover():
    """El teclado funciona con cualquier puntero: no se ata a (hover: none)."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    navegacion = _cuerpo_de_funcion(fuente, "initNavegacionTeclado")

    assert "(hover: none)" not in navegacion
    assert "matchMedia" not in navegacion


def test_js_de_la_navegacion_se_inicializa_despues_de_la_card():
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert re.search(
        r"function init\(\)\s*\{[^}]*initDetailCard\(\)[^}]*initNavegacionTeclado\(\)",
        fuente,
        flags=re.S,
    )


# ========================================================================= #
# Resaltado de la coincidencia dentro de la celda (T5 de p1-periodic-table-e2)
# ========================================================================= #


def test_js_normaliza_con_mapa_de_indices_hacia_el_texto_original():
    """El resaltado necesita trasladar el rango normalizado al texto original.

    NFD desdobla la letra y su acento: 'Hidrógeno' normalizado ocupa menos
    caracteres que el original. La normalización conserva un mapa
    (índice normalizado -> índice fuente) por cada carácter retenido, así
    'hidro' resalta 'Hidró' con el acento intacto.
    """
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "normalizarConMapa")

    assert "NFD" in cuerpo
    # Se registra el índice fuente de cada carácter retenido.
    assert "mapa.push" in cuerpo
    # Las marcas diacríticas del rango combining no aportan índice propio.
    assert "\\u0300" in cuerpo and "\\u036f" in cuerpo


def test_js_marca_la_coincidencia_con_mark_y_la_clase_resaltado():
    """El pop visual es un <mark class="pt-resaltado"> dentro del span."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert "pt-resaltado" in fuente
    assert 'createElement("mark")' in fuente


def test_js_resalta_simbolo_y_nombre_desde_su_texto_canonico():
    """Ambos spans se registran con su texto visible para calcular el rango."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "initTabla")

    assert ".pt-simbolo" in cuerpo
    assert ".pt-nombre" in cuerpo
    assert "simboloOriginal" in cuerpo
    assert "nombreOriginal" in cuerpo


def test_js_restaura_el_texto_plano_al_limpiar_el_resaltado():
    """Al limpiar la búsqueda no debe quedar ningún <mark> en el DOM."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "limpiarResaltado")

    # El texto original vuelve por textContent: los <mark> se descartan.
    assert "textContent" in cuerpo
    assert "original" in cuerpo


def test_js_resalta_solo_las_celdas_que_pasan_el_filtro():
    """El resaltado es una capa visual atada a la búsqueda activa y a `pasa`."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "aplicar")

    assert "hayBusqueda" in cuerpo
    assert "resaltarSpan" in cuerpo
    assert "limpiarResaltado" in cuerpo


def test_js_reutiliza_el_resaltado_cuando_la_busqueda_no_cambia():
    """El hover re-aplica filtros: sin término nuevo no se reconstruyen los marks."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "aplicar")

    # Guard por término buscado: evita reconstruir los <mark> en cada repintado.
    assert "busquedaResaltada" in cuerpo


def test_js_del_resaltado_no_modifica_atributos_accesibles():
    """El resaltado es puramente visual: no toca aria-label ni data-*."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "resaltarSpan")

    assert "setAttribute" not in cuerpo
    assert "aria" not in cuerpo


def test_css_define_el_resaltado_de_la_coincidencia():
    """La banda del resultado visible existe como regla propia."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    bloque = re.search(r"\.pt-resaltado\s*\{([^}]*)\}", sin_comentarios)
    assert bloque, "sin regla .pt-resaltado"
    cuerpo = bloque.group(1)
    # Color heredado del tema: el <mark> no impone su propio color de texto.
    assert "color: inherit" in cuerpo
    assert "padding: 0" in cuerpo


def test_css_del_resaltado_es_visible_en_ambos_temas():
    """El fondo del resaltado sale de una variable declarada por tema."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    bloque = re.search(r"\.pt-resaltado\s*\{([^}]*)\}", sin_comentarios)
    assert bloque, "sin regla .pt-resaltado"
    assert "var(--pt-resaltado" in bloque.group(1)
    # La variable se declara una vez por tema (claro/oscuro).
    assert sin_comentarios.count("--pt-resaltado:") == 2


# ========================================================================= #
# Entrada escalonada de la grilla (T6 de p1-periodic-table-e2)
# ========================================================================= #


def test_celdas_exponen_el_numero_atomico_para_la_entrada_escalonada(
    client, elementos_cargados
):
    """Cada celda emite --pt-z: el CSS calcula el retardo con el número atómico.

    La variable va en el style inline que la celda ya usa para su posición, así
    el bloque f conserva grid-column/grid-row y suma el retardo de la entrada.
    """
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    hidrogeno = _celda_de_simbolo(html, "H")
    assert "--pt-z: 1;" in hidrogeno

    cerio = _celda_de_simbolo(html, "Ce")
    assert "--pt-z: 58;" in cerio
    # La posición inline del bloque f sigue intacta junto a la variable.
    assert "grid-column: 4;" in cerio and "grid-row: 9;" in cerio


def test_celda_sin_detalle_igual_expone_la_variable_de_entrada(client):
    """Sin DetalleElemento no hay fila, pero la celda igual declara --pt-z."""
    ElementoQuimico.objects.create(
        numero_atomico_elemento=999,
        simbolo_elemento="Xx",
        nombre_elemento="Elemento sin detalle",
        peso_atomico_elemento=1,
    )
    html = client.get(reverse("elemento_lista"), {"vista": "tabla"}).content.decode()

    celda = _celda_de_simbolo(html, "Xx")
    assert "--pt-z: 999;" in celda
    # Sin posición en la grilla, pero con el style inline de la animación.
    assert "grid-column" not in celda and "grid-row" not in celda


def test_js_de_la_entrada_escalonada_corre_una_vez_por_sesion():
    """El flag de sessionStorage evita repetir la animación en la misma pestaña."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "initEntradaAnimada")

    assert "ptEntradaAnimada" in cuerpo
    assert "sessionStorage" in cuerpo
    # La lectura va protegida: si el storage no está disponible se asume ya
    # animada (nunca se reanima en cada carga de un modo privado).
    assert "try" in cuerpo and "catch" in cuerpo


def test_js_de_la_entrada_escalonada_activa_y_limpia_la_clase():
    """La animación vive en .pt-animando y se retira al terminar la secuencia."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "initEntradaAnimada")

    assert 'classList.add("pt-animando")' in cuerpo
    assert 'classList.remove("pt-animando")' in cuerpo
    # La limpieza es por temporizador: una sola espera, sin listener por celda.
    assert "setTimeout" in cuerpo


def test_js_de_la_entrada_escalonada_respeta_el_movimiento_reducido():
    """Con prefers-reduced-motion: reduce no se agrega la clase que anima."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")
    cuerpo = _cuerpo_de_funcion(fuente, "initEntradaAnimada")

    assert "(prefers-reduced-motion: reduce)" in cuerpo
    assert "matchMedia" in cuerpo


def test_js_de_la_entrada_escalonada_se_inicializa_al_final():
    """La entrada corre después de la navegación: no compite con el foco inicial."""
    fuente = PERIODIC_TABLE_JS.read_text(encoding="utf-8")

    assert re.search(
        r"function init\(\)\s*\{[^}]*initNavegacionTeclado\(\)[^}]*initEntradaAnimada\(\)",
        fuente,
        flags=re.S,
    )


def test_css_define_la_entrada_escalonada_de_la_grilla():
    """La animación existe como keyframes y se aplica solo bajo .pt-animando."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    assert "@keyframes pt-entrada" in sin_comentarios
    bloque = re.search(r"\.pt-animando\s+\.pt-celda\s*\{([^}]*)\}", sin_comentarios)
    assert bloque, "sin regla .pt-animando .pt-celda"
    cuerpo = bloque.group(1)
    # El relleno hacia atrás mantiene la celda oculta durante su delay y la
    # deja visible si la animación nunca corre.
    assert "animation-fill-mode: backwards" in cuerpo
    # Retardo proporcional a Z: H (Z=1) entra primero, Og (Z=118) al final.
    assert re.search(r"calc\(\(var\(--pt-z[^)]*\)\s*-\s*1\)\s*\*\s*12ms\)", cuerpo)


def test_css_de_la_entrada_escalonada_respeta_el_movimiento_reducido():
    """Dentro del bloque reduce, las celdas animadas quedan sin animación."""
    css = PERIODIC_TABLE_CSS.read_text(encoding="utf-8")
    sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    bloques = re.findall(
        r"@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*"
        r"\{(?:[^{}]|\{[^{}]*\})*\}",
        sin_comentarios,
        flags=re.S,
    )
    animados = [bloque for bloque in bloques if ".pt-animando" in bloque]
    assert animados, "sin bloque reduce para la entrada escalonada"
    assert re.search(
        r"\.pt-animando\s+\.pt-celda\s*\{[^}]*animation:\s*none", animados[0]
    )
