// Filtros del cliente para la vista de tabla periódica (?vista=tabla).
// Semántica sellada (obs #527): los tres filtros se combinan con AND; nunca
// se quitan celdas, solo se atenúan (.pt-dim) o se destacan (.pt-destacada).
// Sin dependencias: vanilla JS.
(function () {
    "use strict";

    // Normaliza texto para buscar sin distinguir mayúsculas ni diacríticos:
    // 'quimica' debe encontrar 'Química'. NFD separa la letra del acento y el
    // rango de combining marks (U+0300-U+036F) los elimina.
    function normalizar(texto) {
        return texto
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function initTabla() {
        var tabla = document.getElementById("pt-tabla");
        // La grilla solo existe en la vista tabla: en tarjetas y en otras
        // páginas el script no hace nada.
        if (!tabla) {
            return;
        }

        // Celdas con sus data-* leídos una sola vez.
        var celdas = Array.prototype.slice
            .call(tabla.querySelectorAll(".pt-celda"))
            .map(function (celda) {
                return {
                    el: celda,
                    categoria: celda.getAttribute("data-categoria") || "",
                    simbolo: normalizar(celda.getAttribute("data-simbolo") || ""),
                    nombre: normalizar(celda.getAttribute("data-nombre") || ""),
                    peso: parseFloat(celda.getAttribute("data-peso")),
                };
            });

        // Cada chip puede representar una categoría fina (data-categoria) o una
        // familia (data-categorias, categorías separadas por "|"). El chip
        // activo filtra por el conjunto completo de categorías que representa.
        function categoriasDeChip(chip) {
            var multi = chip.getAttribute("data-categorias");
            if (multi) {
                return multi.split("|").filter(function (valor) {
                    return valor !== "";
                });
            }
            var simple = chip.getAttribute("data-categoria");
            return simple ? [simple] : [];
        }

        var chips = Array.prototype.slice
            .call(document.querySelectorAll("#pt-leyenda .pt-chip"))
            .map(function (chip) {
                return {
                    el: chip,
                    // Identidad estable del chip para el estado del click.
                    valor:
                        chip.getAttribute("data-categoria") ||
                        chip.getAttribute("data-categorias") ||
                        "",
                    categorias: categoriasDeChip(chip),
                };
            });
        var inputBuscar = document.getElementById("pt-buscar");
        var inputPeso = document.getElementById("pt-peso-min");

        // Estado persistente (click) y categorías de vista previa (hover).
        var estado = {
            valorCategoria: null,
            categorias: null,
            busqueda: "",
            pesoMin: null,
        };
        var categoriasPrevias = null;

        // rAF para agrupar varios eventos seguidos en un solo repintado.
        var raf = window.requestAnimationFrame || function (cb) {
            return window.setTimeout(cb, 16);
        };
        var pendiente = false;

        function programar() {
            if (pendiente) {
                return;
            }
            pendiente = true;
            raf(function () {
                pendiente = false;
                aplicar(filtroEfectivo());
            });
        }

        // El hover manda sobre la categoría persistente; los demás filtros
        // siguen activos (los tres se combinan con AND).
        function filtroEfectivo() {
            return {
                categorias:
                    categoriasPrevias !== null
                        ? categoriasPrevias
                        : estado.categorias,
                busqueda: estado.busqueda,
                pesoMin: estado.pesoMin,
            };
        }

        function aplicar(filtro) {
            var buscando = filtro.busqueda;
            var hayCategoria =
                filtro.categorias !== null && filtro.categorias.length > 0;
            var hayBusqueda = buscando !== "";
            var hayPeso = filtro.pesoMin !== null;
            var hayFiltro = hayCategoria || hayBusqueda || hayPeso;

            celdas.forEach(function (celda) {
                var pasa = true;
                if (hayCategoria && filtro.categorias.indexOf(celda.categoria) === -1) {
                    pasa = false;
                }
                if (pasa && hayBusqueda) {
                    pasa =
                        celda.simbolo.indexOf(buscando) !== -1 ||
                        celda.nombre.indexOf(buscando) !== -1;
                }
                if (pasa && hayPeso) {
                    pasa = !isNaN(celda.peso) && celda.peso >= filtro.pesoMin;
                }

                // Sin filtros activos: todas las celdas neutrales.
                celda.el.classList.remove("pt-dim", "pt-destacada");
                if (hayFiltro) {
                    celda.el.classList.add(pasa ? "pt-destacada" : "pt-dim");
                }
            });
        }

        // Marca el chip activo para el estilo [aria-pressed="true"] del CSS.
        function actualizarChips() {
            chips.forEach(function (chip) {
                var activo =
                    chip.valor !== "" && chip.valor === estado.valorCategoria;
                chip.el.setAttribute("aria-pressed", activo ? "true" : "false");
            });
        }

        chips.forEach(function (chip) {
            chip.el.addEventListener("click", function () {
                var mismo =
                    estado.valorCategoria !== null &&
                    estado.valorCategoria === chip.valor;
                estado.valorCategoria = mismo ? null : chip.valor;
                estado.categorias = mismo ? null : chip.categorias;
                actualizarChips();
                programar();
            });
            // Vista previa temporal: no toca el estado del click.
            chip.el.addEventListener("mouseover", function () {
                categoriasPrevias = chip.categorias;
                programar();
            });
            chip.el.addEventListener("mouseout", function () {
                categoriasPrevias = null;
                programar();
            });
        });

        if (inputBuscar) {
            inputBuscar.addEventListener("input", function () {
                estado.busqueda = normalizar(inputBuscar.value.trim());
                programar();
            });
        }

        if (inputPeso) {
            inputPeso.addEventListener("input", function () {
                var valor = parseFloat(inputPeso.value);
                estado.pesoMin = isNaN(valor) ? null : valor;
                programar();
            });
        }

        // Estado inicial: recupera valores ya presentes en los inputs
        // (p. ej. el peso mínimo precargado desde el GET).
        if (inputBuscar && inputBuscar.value.trim() !== "") {
            estado.busqueda = normalizar(inputBuscar.value.trim());
        }
        if (inputPeso && inputPeso.value.trim() !== "") {
            var inicial = parseFloat(inputPeso.value);
            estado.pesoMin = isNaN(inicial) ? null : inicial;
        }
        actualizarChips();
        aplicar(filtroEfectivo());
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initTabla);
    } else {
        initTabla();
    }
})();
