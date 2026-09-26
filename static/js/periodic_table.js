// Filtros del cliente para la vista de tabla periódica (?vista=tabla).
// También recuerda la última vista elegida en el selector (?vista=tarjetas|tabla).
// Semántica sellada (obs #527): los tres filtros se combinan con AND; nunca
// se quitan celdas, solo se atenúan (.pt-dim) o se destacan (.pt-destacada).
// Sin dependencias: vanilla JS.
(function () {
    "use strict";

    // Preferencia de vista: al tocar uno de los dos botones del selector se
    // guarda la vista destino para la próxima visita. Es delegación de eventos
    // y corre en AMBAS vistas: el guardado no depende de que exista la grilla.
    // Nunca se escribe fuera de un click explícito.
    function initPreferenciaVista() {
        // Guard idempotente: un doble include no duplica listeners.
        if (window.gestorQuimicoVistaElementos) {
            return;
        }
        window.gestorQuimicoVistaElementos = true;

        var STORAGE_KEY = "gestorQuimicoVistaElementos";

        document.addEventListener("click", function (event) {
            var objetivo = event.target;
            if (!objetivo || !objetivo.closest) {
                return;
            }
            var enlace = objetivo.closest("a");
            if (!enlace) {
                return;
            }
            var href = enlace.getAttribute("href") || "";
            // Solo los enlaces del selector llevan la vista en la URL.
            if (href.indexOf("vista=") === -1) {
                return;
            }
            var vista = null;
            if (href.indexOf("vista=tabla") !== -1) {
                vista = "tabla";
            } else if (href.indexOf("vista=tarjetas") !== -1) {
                vista = "tarjetas";
            }
            if (vista === null) {
                return;
            }
            try {
                window.localStorage.setItem(STORAGE_KEY, vista);
            } catch (error) {
                // Storage no disponible (p. ej. modo privado): se ignora.
            }
            // Sin preventDefault: la navegación sigue y el servidor honra el
            // ?vista explícito del enlace.
        });
    }

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

    // Tarjeta de detalle (T3 de la entrega 2): una única card flotante con los
    // datos de la celda apuntada con el mouse o el teclado. Todo sale de los
    // data-* de la celda: cero peticiones al servidor. La card no captura el
    // puntero (pointer-events: none en el CSS), así que el hover nunca se
    // realimenta; en touch no se activa porque un tap navega directo al
    // detalle (las celdas son <a>).
    function initDetailCard() {
        var tabla = document.getElementById("pt-tabla");
        var card = document.getElementById("pt-card");
        // La card solo tiene sentido junto a la grilla de la vista tabla.
        if (!tabla || !card) {
            return;
        }
        // Dispositivos sin hover real (touch): el tap navega, no hay peek.
        if (window.matchMedia && window.matchMedia("(hover: none)").matches) {
            return;
        }
        // Guard idempotente: un doble include no duplica listeners.
        if (window.gestorQuimicoPtCard) {
            return;
        }
        window.gestorQuimicoPtCard = true;

        var MARGEN = 8;
        var celdaVisible = null;

        function crear(tag, clase, texto) {
            var nodo = document.createElement(tag);
            if (clase) {
                nodo.className = clase;
            }
            if (texto) {
                nodo.textContent = texto;
            }
            return nodo;
        }

        // Sin valor no se dibuja la fila: nada se inventa.
        function agregarDato(lista, etiqueta, valor) {
            if (!valor) {
                return;
            }
            lista.appendChild(crear("dt", null, etiqueta));
            lista.appendChild(crear("dd", null, valor));
        }

        function rellenar(celda) {
            var z = celda.querySelector(".pt-z");
            var cabecera = crear("div", "pt-card-cabecera");
            var lineaZ = crear("span", "pt-card-z");
            // Rótulo textual del número atómico: 'Z=26' es etiqueta, no texto

            // pegado al símbolo ('26' contra 'Fe...' se leía como una sola
            // palabra).
            lineaZ.appendChild(crear("span", "pt-card-z-rotulo", "Z="));
            lineaZ.appendChild(crear("span", "pt-card-z-valor", z ? z.textContent : ""));
            cabecera.appendChild(lineaZ);
            // Corchetes cuadrados alrededor del símbolo: distinguen el
            // elemento de su nombre al leer la card de corrido.
            cabecera.appendChild(crear("span", "pt-card-simbolo", "["));
            cabecera.appendChild(
                crear("span", "pt-card-simbolo-valor", celda.getAttribute("data-simbolo-display"))
            );
            cabecera.appendChild(crear("span", "pt-card-simbolo", "]"));
            cabecera.appendChild(
                crear("span", "pt-card-nombre", celda.getAttribute("data-nombre-display"))
            );
            var datos = crear("dl", "pt-card-datos mb-0");
            agregarDato(datos, "Categoría", celda.getAttribute("data-categoria"));
            var grupo = celda.getAttribute("data-grupo");
            var periodo = celda.getAttribute("data-periodo");
            if (grupo && periodo) {
                agregarDato(datos, "Grupo/Período", grupo + " / " + periodo);
            }
            // Honestidad del dato: un valor entre corchetes es número másico
            // de un isótopo representativo, no el peso atómico estándar.
            var masico = celda.getAttribute("data-peso-masico") === "1";
            var peso = celda.getAttribute("data-peso-mostrar");
            if (peso) {
                agregarDato(
                    datos,
                    masico ? "Número másico" : "Peso atómico",
                    masico ? peso : peso + " g/mol"
                );
            }

            card.textContent = "";
            card.appendChild(cabecera);
            card.appendChild(datos);
            card.appendChild(crear("div", "pt-card-hint", "Ver detalle"));
        }

        // Posiciona la card junto a la celda, acotada al viewport: no se sale
        // por el borde derecho ni por abajo. Usa coordenadas de página
        // (rect + scroll) porque la card vive en el flujo normal.
        function posicionar(celda) {
            var rect = celda.getBoundingClientRect();
            var ancho = card.offsetWidth;
            var alto = card.offsetHeight;
            var scrollX = window.scrollX || window.pageXOffset || 0;
            var scrollY = window.scrollY || window.pageYOffset || 0;
            var vistaAncho = document.documentElement.clientWidth;
            var vistaAlto = document.documentElement.clientHeight;

            var izq = rect.right + scrollX + MARGEN;
            if (izq + ancho > scrollX + vistaAncho - MARGEN) {
                // No entra a la derecha: se pasa al lado izquierdo de la celda.
                izq = rect.left + scrollX - ancho - MARGEN;
            }
            izq = Math.max(izq, scrollX + MARGEN);
            izq = Math.min(izq, scrollX + vistaAncho - ancho - MARGEN);

            var arriba = rect.top + scrollY;
            arriba = Math.min(arriba, scrollY + vistaAlto - alto - MARGEN);
            arriba = Math.max(arriba, scrollY + MARGEN);

            card.style.left = izq + "px";
            card.style.top = arriba + "px";
        }

        function mostrar(celda) {
            if (celda === celdaVisible) {
                return;
            }
            celdaVisible = celda;
            rellenar(celda);
            card.hidden = false;
            // Reflow forzado: fija el estado inicial (opacidad 0) antes de
            // la clase visible, si no el fundido no se ve.
            void card.offsetWidth;
            card.classList.add("pt-card-visible");
            card.setAttribute("aria-hidden", "false");
            posicionar(celda);
        }

        function ocultar() {
            if (!celdaVisible) {
                return;
            }
            celdaVisible = null;
            card.classList.remove("pt-card-visible");
            card.setAttribute("aria-hidden", "true");
            card.hidden = true;
        }

        function celdaDeEvento(event) {
            var objetivo = event.target;
            if (!objetivo || !objetivo.closest) {
                return null;
            }
            return objetivo.closest(".pt-celda");
        }

        // El mouse entra o sale de la celda: la card sigue el mismo ciclo.
        tabla.addEventListener("mouseover", function (event) {
            var celda = celdaDeEvento(event);
            if (celda) {
                mostrar(celda);
            }
        });
        tabla.addEventListener("mouseout", function (event) {
            var celda = celdaDeEvento(event);
            var destino = event.relatedTarget;
            if (!celda || !destino || !celda.contains(destino)) {
                ocultar();
            }
        });
        // Teclado: misma card al enfocar la celda (accesibilidad).
        tabla.addEventListener("focusin", function (event) {
            var celda = celdaDeEvento(event);
            if (celda) {
                mostrar(celda);
            }
        });
        tabla.addEventListener("focusout", function (event) {
            var celda = celdaDeEvento(event);
            var destino = event.relatedTarget;
            if (!celda || !destino || !celda.contains(destino)) {
                ocultar();
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                ocultar();
            }
        });
        // Al scrollear la card quedaría despegada de su celda: se oculta. En
        // captura (no burbujea) porque la grilla también hace scroll interno.
        window.addEventListener("scroll", ocultar, { passive: true, capture: true });
    }

    function init() {
        initPreferenciaVista();
        initTabla();
        initDetailCard();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
