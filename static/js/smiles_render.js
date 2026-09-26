/**
 * Client-side 2D structure rendering for compounds that carry a SMILES string.
 *
 * Feature p2-2d-diagrams (Entrega 1), task T5.
 * Feature p2-2d-diagrams-e4-modal-zoom, task T2: the drawing core is now
 * reusable so the same SMILES can be re-drawn at modal size.
 *
 * Contract:
 * - Fully optional: if there is no [data-smiles] element, or the vendored
 *   SmilesDrawer global is missing, this script does nothing (fail soft).
 * - Diagrams are drawn as inline SVG via SmilesDrawer.SvgDrawer (crisper than
 *   canvas and free of the canvas backing-store issues). Structures are drawn
 *   with SmilesDrawer's fixed "light" theme and sit on a FIXED light
 *   background (see .estructura-2d / .estructura-2d-modal in styles.css) so
 *   the chemistry stays readable even when the page uses data-bs-theme="dark".
 * - The vendored global is `SmilesDrawer` (window.SmilesDrawer) exposing
 *   `SvgDrawer` and `parse`; verified against
 *   static/vendor/smilesdrawer/smiles-drawer.min.js.
 * - The zoom modal is native Bootstrap 5: this script only opens the shared
 *   modal element (bootstrap.Modal.getOrCreateInstance) and paints the SVG
 *   inside it. Closing (X, ESC, click outside) is 100% BS5 behavior; there is
 *   no custom modal open/close code here.
 *
 * Each container is expected to look like:
 *   <div class="estructura-2d" data-smiles="CCO" data-smiles-zoom tabindex="0"
 *        data-smiles-width="200" data-smiles-height="150"></div>
 * and each zoom trigger next to it:
 *   <button type="button" data-smiles-ampliar="CCO">Ampliar</button>
 */
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var DEFAULT_WIDTH = 200;
  var DEFAULT_HEIGHT = 150;
  // Fixed modal re-draw size: the SVG is generated at these native dimensions
  // (crisp vector), never a stretched bitmap of the miniature.
  var MODAL_WIDTH = 600;
  var MODAL_HEIGHT = 450;
  var MODAL_ID = "modal-estructura-2d";
  var MODAL_BODY_ATTR = "data-smiles-modal-body";
  var ATRIBUTO_ZOOM = "data-smiles-zoom";
  var ATRIBUTO_AMPLIAR = "data-smiles-ampliar";

  function readSize(element, attribute, fallback) {
    var raw = parseInt(element.getAttribute(attribute), 10);
    return isNaN(raw) || raw <= 0 ? fallback : raw;
  }

  // Fail soft when the vendored global is missing or does not expose the API
  // this script relies on.
  function smilesDrawerDisponible() {
    return !(
      typeof SmilesDrawer === "undefined" ||
      !SmilesDrawer ||
      typeof SmilesDrawer.SvgDrawer !== "function" ||
      typeof SmilesDrawer.parse !== "function"
    );
  }

  // SmilesDrawer centers molecules by their atom coordinates only; bracket
  // atom labels such as "Na+"/"Cl−" render as text wider than the coordinate
  // bounds, which visually shifts multi-fragment diagrams (e.g. [Na+].[Cl-])
  // to one side. After drawing, the drawer overwrites the svg viewBox with
  // the drawing bounds ("minX minY width height") in its own coordinate
  // space. Recenter the whole ink within THAT viewBox: wrap the content in a
  // group and translate it so the true bounding box (getBBox includes text
  // geometry) sits at the center of the viewBox. Fail soft: without a
  // readable viewBox or getBBox, keep the drawing as produced.
  function centrarContenido(svg) {
    var viewBox = svg.getAttribute("viewBox");
    if (!viewBox) {
      return;
    }
    var partes = viewBox.trim().split(/[\s,]+/).map(Number);
    if (partes.length !== 4 || partes.some(isNaN) || partes[2] <= 0 || partes[3] <= 0) {
      return;
    }
    var contenido;
    try {
      contenido = document.createElementNS(SVG_NS, "g");
      while (svg.firstChild) {
        contenido.appendChild(svg.firstChild);
      }
      svg.appendChild(contenido);
      var caja = contenido.getBBox();
      if (!caja || !isFinite(caja.width) || caja.width <= 0) {
        return;
      }
      var centroVbX = partes[0] + partes[2] / 2;
      var centroVbY = partes[1] + partes[3] / 2;
      var dx = centroVbX - (caja.x + caja.width / 2);
      var dy = centroVbY - (caja.y + caja.height / 2);
      if (isFinite(dx) && isFinite(dy)) {
        contenido.setAttribute("transform", "translate(" + dx + " " + dy + ")");
      }
    } catch (error) {
      return;
    }
  }

  function crearSvg(width, height) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("xmlns", SVG_NS);
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Estructura 2D del compuesto");
    return svg;
  }

  // Core reusable drawing: parse `smiles` and return a freshly drawn SVG sized
  // `width` x `height`, or null on any parse/draw failure (same fail soft as
  // before). The SVG is detached on purpose: callers insert it into the DOM
  // first so `centrarContenido` can read its real geometry (getBBox needs the
  // element rendered). SmilesDrawer.parse is synchronous in the vendored
  // bundle, so the return value is already resolved.
  function dibujarSvg(smiles, width, height) {
    var dibujado = null;
    SmilesDrawer.parse(
      smiles,
      function (tree) {
        var svg = crearSvg(width, height);
        try {
          var drawer = new SmilesDrawer.SvgDrawer({
            width: width,
            height: height,
          });
          drawer.draw(tree, svg, "light");
          dibujado = svg;
        } catch (error) {
          // Drawing failed: return nothing instead of a half-drawn SVG. The
          // server-side pysmiles validation should prevent this, so this only
          // guards tampered data or a library edge case.
          dibujado = null;
        }
      },
      function () {
        // Unparseable SMILES: fail soft. The server already validated it.
        dibujado = null;
      }
    );
    return dibujado;
  }

  // Attach a drawn SVG and recenter its ink. Insertion MUST happen before
  // centering: getBBox returns zeros for a detached (or display:none) node.
  function insertarSvg(svg, contenedor) {
    contenedor.appendChild(svg);
    centrarContenido(svg);
  }

  function renderOne(container, smiles) {
    var width = readSize(container, "data-smiles-width", DEFAULT_WIDTH);
    var height = readSize(container, "data-smiles-height", DEFAULT_HEIGHT);
    var svg = dibujarSvg(smiles, width, height);
    if (svg) {
      insertarSvg(svg, container);
    }
  }

  // --- Modal zoom (native Bootstrap 5) ---

  function cuerpoDelModal() {
    var modal = document.getElementById(MODAL_ID);
    if (!modal) {
      return null;
    }
    return modal.querySelector("[" + MODAL_BODY_ATTR + "]");
  }

  function mostrarAvisoModal(cuerpo) {
    var aviso = document.createElement("p");
    aviso.className = "estructura-2d-modal__aviso text-muted mb-0";
    aviso.textContent = "No se pudo generar la estructura 2D.";
    cuerpo.appendChild(aviso);
  }

  function abrirModalZoom(smiles) {
    var modal = document.getElementById(MODAL_ID);
    var cuerpo = cuerpoDelModal();
    if (!modal || !cuerpo) {
      return;
    }

    // Show the native modal BEFORE drawing: a hidden .modal is display:none,
    // and centrarContenido (getBBox) would read an empty box. Bootstrap sets
    // display:block synchronously inside show().
    if (window.bootstrap && window.bootstrap.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(modal).show();
    }

    cuerpo.innerHTML = "";
    if (smilesDrawerDisponible()) {
      var svg = dibujarSvg(smiles, MODAL_WIDTH, MODAL_HEIGHT);
      if (svg) {
        insertarSvg(svg, cuerpo);
        return;
      }
    }
    mostrarAvisoModal(cuerpo);
  }

  // Closest ancestor (or self) carrying a zoom trigger. Small parent walk
  // instead of Element.closest() to keep the file's ES5-ish style.
  function buscarDisparador(nodo) {
    while (nodo && nodo.nodeType) {
      if (
        nodo.nodeType === 1 &&
        (nodo.hasAttribute(ATRIBUTO_ZOOM) || nodo.hasAttribute(ATRIBUTO_AMPLIAR))
      ) {
        return nodo;
      }
      nodo = nodo.parentNode;
    }
    return null;
  }

  function smilesDelDisparador(disparador) {
    if (disparador.hasAttribute(ATRIBUTO_AMPLIAR)) {
      return disparador.getAttribute(ATRIBUTO_AMPLIAR);
    }
    return disparador.getAttribute("data-smiles");
  }

  function manejarClick(evento) {
    var disparador = buscarDisparador(evento.target);
    if (!disparador) {
      return;
    }
    var smiles = smilesDelDisparador(disparador);
    if (!smiles) {
      return;
    }
    evento.preventDefault();
    abrirModalZoom(smiles);
  }

  function manejarTeclado(evento) {
    if (evento.key !== "Enter" && evento.key !== " ") {
      return;
    }
    var disparador = buscarDisparador(evento.target);
    // <button> already emits a native click on Enter/Space; only the
    // tabindex container needs this keyboard path.
    if (!disparador || !disparador.hasAttribute(ATRIBUTO_ZOOM)) {
      return;
    }
    var smiles = smilesDelDisparador(disparador);
    if (!smiles) {
      return;
    }
    evento.preventDefault();
    abrirModalZoom(smiles);
  }

  function initSmilesRender() {
    var contenedores = document.querySelectorAll("[data-smiles]");
    var disparadores = document.querySelectorAll(
      "[" + ATRIBUTO_ZOOM + "], [" + ATRIBUTO_AMPLIAR + "]"
    );

    if (contenedores.length && smilesDrawerDisponible()) {
      Array.prototype.forEach.call(contenedores, function (container) {
        var smiles = container.getAttribute("data-smiles");
        if (smiles) {
          renderOne(container, smiles);
        }
      });
    }

    // Modal wiring is independent of SmilesDrawer: without the library the
    // modal still opens and shows its fail-soft message.
    if (disparadores.length) {
      document.addEventListener("click", manejarClick);
      document.addEventListener("keydown", manejarTeclado);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSmilesRender);
  } else {
    initSmilesRender();
  }
})();
