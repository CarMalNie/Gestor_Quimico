/**
 * Selector de estructura por fórmula (p2-2d-diagrams-e3-isomeros).
 *
 * Contract:
 * - Botón #smiles-buscar en la sección #estructura2d: consulta al endpoint
 *   GET lookup-isomeros usando la FÓRMULA MOLECULAR escrita en el campo
 *   formula_compuesto (campo obligatorio del form, independiente del
 *   idioma del nombre).
 * - Un solo isómero -> rellena #id_smiles directo + mensaje de éxito.
 * - Varios -> lista de opciones clickeables (nombre + SMILES) en
 *   #lookup-resultados; al elegir una, se rellena el campo.
 * - En 404 (fórmula sin resultados) o 502 (servicio caído) muestra el
 *   mensaje correspondiente y el enlace manual a PubChem precargado CON
 *   LA FÓRMULA (idioma-agnóstico: PubChem muestra la misma lista de
 *   isómeros y el usuario elige a mano).
 * - Fail soft: si falta algún elemento del DOM, este script no hace nada.
 * - Español neutro en todos los mensajes (decisión del operador).
 */
(function () {
  "use strict";

  var boton = document.getElementById("smiles-buscar");
  var inputSmiles = document.getElementById("id_smiles");
  var inputFormula = document.getElementById("id_formula_compuesto");
  var mensaje = document.getElementById("lookup-mensaje");
  var enlacePubChem = document.getElementById("lookup-pubchem");
  var resultados = document.getElementById("lookup-resultados");

  if (!boton || !inputSmiles || !inputFormula || !mensaje || !enlacePubChem) {
    return;
  }

  var urlEndpoint = boton.getAttribute("data-lookup-url");
  var textoOriginalBoton = boton.textContent;

  function mostrar(texto, variante) {
    mensaje.textContent = texto;
    mensaje.className = "small mt-2 " + variante;
    mensaje.hidden = false;
  }

  function enlacePubChemConFormula(formula) {
    enlacePubChem.href =
      "https://pubchem.ncbi.nlm.nih.gov/#query=" + encodeURIComponent(formula);
    // Sin display utility: el atributo hidden manda hasta que hace falta.
    enlacePubChem.hidden = false;
  }

  function ocultarEnlace() {
    enlacePubChem.hidden = true;
  }

  function limpiarResultados() {
    if (resultados) {
      resultados.textContent = "";
      resultados.hidden = true;
    }
  }

  function usarCandidato(candidato) {
    inputSmiles.value = candidato.smiles;
    limpiarResultados();
    mostrar(
      "Estructura cargada (" + candidato.nombre +
      "). Revísela y edítela si es necesario antes de guardar.",
      "text-success"
    );
  }

  function mostrarCandidatos(candidatos, formula) {
    if (!resultados) {
      usarCandidatoDirecto(candidatos[0]);
      return;
    }
    resultados.textContent = "";
    candidatos.forEach(function (candidato) {
      var opcion = document.createElement("button");
      opcion.type = "button";
      opcion.className = "list-group-item list-group-item-action py-2";
      opcion.textContent = candidato.nombre + " — " + candidato.smiles;
      opcion.addEventListener("click", function () {
        usarCandidato(candidato);
      });
      resultados.appendChild(opcion);
    });
    resultados.hidden = false;
    mostrar(
      "La fórmula " + formula + " corresponde a varias estructuras. " +
      "Elija la que corresponde a su compuesto:",
      "text-muted"
    );
  }

  function usarCandidatoDirecto(candidato) {
    inputSmiles.value = candidato.smiles;
    mostrar(
      "Estructura cargada (" + candidato.nombre +
      "). Revísela y edítela si es necesario antes de guardar.",
      "text-success"
    );
  }

  boton.addEventListener("click", function () {
    var formula = inputFormula.value.trim();
    if (!formula) {
      limpiarResultados();
      ocultarEnlace();
      mostrar(
        "Escriba primero la fórmula molecular del compuesto y luego busque la estructura.",
        "text-muted"
      );
      return;
    }

    boton.disabled = true;
    boton.textContent = "Buscando…";
    limpiarResultados();
    ocultarEnlace();
    mostrar("Buscando estructuras para " + formula + "…", "text-muted");

    fetch(urlEndpoint + "?formula=" + encodeURIComponent(formula))
      .then(function (respuesta) {
        return respuesta.json().then(function (cuerpo) {
          return { estado: respuesta.status, cuerpo: cuerpo };
        });
      })
      .then(function (resultado) {
        if (resultado.estado === 200) {
          var candidatos = resultado.cuerpo.candidatos;
          if (candidatos.length === 1) {
            usarCandidatoDirecto(candidatos[0]);
          } else {
            mostrarCandidatos(candidatos, resultado.cuerpo.formula);
          }
        } else if (resultado.estado === 404) {
          mostrar(
            "No se encontraron estructuras para la fórmula " + formula +
            ". Puede revisar la fórmula, buscar en PubChem y pegar el SMILES manualmente.",
            "text-warning"
          );
          enlacePubChemConFormula(formula);
        } else {
          mostrar(
            "El servicio de búsqueda no está disponible en este momento. " +
            "Puede buscar la fórmula en PubChem y pegar el SMILES manualmente.",
            "text-warning"
          );
          enlacePubChemConFormula(formula);
        }
      })
      .catch(function () {
        mostrar(
          "No se pudo contactar el servicio de búsqueda. Verifique su " +
          "conexión e intente de nuevo, o pegue el SMILES manualmente.",
          "text-warning"
        );
      })
      .finally(function () {
        boton.disabled = false;
        boton.textContent = textoOriginalBoton;
      });
  });
})();
