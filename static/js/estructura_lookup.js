/**
 * Búsqueda automática de estructura por nombre (p2-2d-diagrams-e2-lookup).
 *
 * Contract:
 * - Botón #smiles-buscar dentro de la sección #estructura2d: consulta al
 *   endpoint GET lookup-estructura usando el nombre escrito en el campo
 *   nombre_compuesto y rellena el input #id_smiles si el resolver responde.
 * - Fail soft: si falta algún elemento del DOM, este script no hace nada.
 * - En 404 (nombre desconocido) o 502 (servidor caído) muestra el mensaje
 *   correspondiente y el enlace manual a PubChem con la búsqueda precargada.
 * - Español neutro en todos los mensajes (decisión de diseño del operador).
 */
(function () {
  "use strict";

  var boton = document.getElementById("smiles-buscar");
  var inputSmiles = document.getElementById("id_smiles");
  var inputNombre = document.getElementById("id_nombre_compuesto");
  var mensaje = document.getElementById("lookup-mensaje");
  var enlacePubChem = document.getElementById("lookup-pubchem");

  if (!boton || !inputSmiles || !inputNombre || !mensaje || !enlacePubChem) {
    return;
  }

  var urlEndpoint = boton.getAttribute("data-lookup-url");
  var textoOriginalBoton = boton.textContent;

  function mostrar(texto, variante) {
    mensaje.textContent = texto;
    mensaje.className = "small mt-2 " + variante;
    mensaje.hidden = false;
  }

  function enlacesPubChem(nombre) {
    enlacePubChem.href =
      "https://pubchem.ncbi.nlm.nih.gov/#query=" + encodeURIComponent(nombre);
    enlacePubChem.hidden = false;
  }

  function ocultarEnlace() {
    enlacePubChem.hidden = true;
  }

  boton.addEventListener("click", function () {
    var nombre = inputNombre.value.trim();
    if (!nombre) {
      ocultarEnlace();
      mostrar(
        "Escriba primero el nombre del compuesto y luego busque la estructura.",
        "text-muted"
      );
      return;
    }

    boton.disabled = true;
    boton.textContent = "Buscando…";
    ocultarEnlace();
    mostrar("Buscando estructura para \"" + nombre + "\"…", "text-muted");

    fetch(urlEndpoint + "?nombre=" + encodeURIComponent(nombre))
      .then(function (respuesta) {
        return respuesta.json().then(function (cuerpo) {
          return { estado: respuesta.status, cuerpo: cuerpo };
        });
      })
      .then(function (resultado) {
        if (resultado.estado === 200) {
          inputSmiles.value = resultado.cuerpo.smiles;
          mostrar(
            "Estructura cargada. Revísela y edítela si es necesario antes de guardar.",
            "text-success"
          );
        } else if (resultado.estado === 404) {
          mostrar(
            "No se encontró una estructura para \"" + nombre +
            "\". Puede buscarla en PubChem y pegar el SMILES manualmente.",
            "text-warning"
          );
          enlacesPubChem(nombre);
        } else {
          mostrar(
            "El servicio de búsqueda no está disponible en este momento. " +
            "Puede buscar la estructura en PubChem y pegar el SMILES manualmente.",
            "text-warning"
          );
          enlacesPubChem(nombre);
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
