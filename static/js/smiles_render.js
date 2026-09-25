/**
 * Client-side 2D structure rendering for compounds that carry a SMILES string.
 *
 * Feature p2-2d-diagrams (Entrega 1), task T5.
 *
 * Contract:
 * - Fully optional: if there is no [data-smiles] element, or the vendored
 *   SmilesDrawer global is missing, this script does nothing (fail soft).
 * - Diagrams are drawn as inline SVG via SmilesDrawer.SvgDrawer (crisper than
 *   canvas and free of the canvas backing-store issues). Structures are drawn
 *   with SmilesDrawer's fixed "light" theme and sit on a FIXED light
 *   background (see .estructura-2d in styles.css) so the chemistry stays
 *   readable even when the page uses data-bs-theme="dark".
 * - The vendored global is `SmilesDrawer` (window.SmilesDrawer) exposing
 *   `SvgDrawer` and `parse`; verified against
 *   static/vendor/smilesdrawer/smiles-drawer.min.js.
 *
 * Each container is expected to look like:
 *   <div class="estructura-2d" data-smiles="CCO"
 *        data-smiles-width="200" data-smiles-height="150"></div>
 */
(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var DEFAULT_WIDTH = 200;
  var DEFAULT_HEIGHT = 150;

  function readSize(element, attribute, fallback) {
    var raw = parseInt(element.getAttribute(attribute), 10);
    return isNaN(raw) || raw <= 0 ? fallback : raw;
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

  function renderOne(container, smiles) {
    var width = readSize(container, "data-smiles-width", DEFAULT_WIDTH);
    var height = readSize(container, "data-smiles-height", DEFAULT_HEIGHT);

    SmilesDrawer.parse(
      smiles,
      function (tree) {
        var svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("xmlns", SVG_NS);
        svg.setAttribute("width", String(width));
        svg.setAttribute("height", String(height));
        svg.setAttribute("viewBox", "0 0 " + width + " " + height);
        svg.setAttribute("role", "img");
        svg.setAttribute("aria-label", "Estructura 2D del compuesto");
        container.appendChild(svg);

        try {
          var drawer = new SmilesDrawer.SvgDrawer({
            width: width,
            height: height,
          });
          drawer.draw(tree, svg, "light");
          centrarContenido(svg);
        } catch (error) {
          // Drawing failed: leave the container empty instead of a half-drawn
          // SVG. The server-side pysmiles validation should prevent this, so
          // this only guards tampered data or a library edge case.
          if (svg.parentNode) {
            svg.parentNode.removeChild(svg);
          }
        }
      },
      function () {
        // Unparseable SMILES: fail soft. The server already validated it.
      }
    );
  }

  function initSmilesRender() {
    var containers = document.querySelectorAll("[data-smiles]");
    if (!containers.length) {
      return;
    }

    if (
      typeof SmilesDrawer === "undefined" ||
      !SmilesDrawer ||
      typeof SmilesDrawer.SvgDrawer !== "function" ||
      typeof SmilesDrawer.parse !== "function"
    ) {
      return;
    }

    Array.prototype.forEach.call(containers, function (container) {
      var smiles = container.getAttribute("data-smiles");
      if (smiles) {
        renderOne(container, smiles);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSmilesRender);
  } else {
    initSmilesRender();
  }
})();
