# Feature: p2-2d-diagrams-e2-lookup — Entrega 2: búsqueda de estructura por nombre

Sealed design (2026-09-25, sesión con operador): lookup automático con
**Cactus resolver** como único motor backend + **link manual a PubChem**
como fallback de UX. PubChem via Python quedó descartado con evidencia
(503 fingerprint-based verificado en PA y local); subprocess-curl quedó
como Entrega 3 opcional documentada (obs Engram p2-entrega2-lookup).

## Evidencia de diseño (spikes verificados)

- Cactus (`cactus.nci.nih.gov/chemical/structure/<nombre>/smiles`):
  HTTP 200 en 0.1s desde PA (consola operador, 23:54); cubierto por la
  wildcard `.nih.gov` de la whitelist PA free. SMILES aromáticos
  minúsculas + estereo cuando aplica.
- PubChem PUG REST: 200 solo vía binario curl; 503 `PUGREST.ServerBusy`
  con clientes Python (urllib/requests) — verificado en PA y local.
- Compatibilidad con la implementación Entrega 1: 10/10 variantes de
  ambos proveedores parsean con pysmiles y son expandibles
  (expandir_heteroatomos). Caveat documentado: pysmiles no reescribe
  estereo (@/@@) tras la expansión de H — no afecta el dibujo didáctico.
- Copy de UI: español neutro (decisión del operador; sin voseo).

## Scope (Entrega 2)

- Endpoint `GET /compuestos/api/lookup-estructura/?nombre=<q>`:
  - Login requerido (JSON 401 si no).
  - Querystring `nombre` obligatorio (400 si falta/vacío).
  - Resuelve con Cactus via urllib stdlib (timeout ~8s, UA propio).
  - Valida el SMILES devuelto con pysmiles (misma lógica que el form:
    parseable y con átomos) — nunca se entrega basura al frontend.
  - Respuestas: 200 `{smiles, fuente}`; 404 `{error: 'no_encontrado'}`
    cuando el resolver no conoce el nombre; 502 `{error:
    'servicio_no_disponible'}` en timeout/5xx upstream.
- Frontend (`compuesto_form.html`, dentro de la sección 2D plegada):
  - Botón "Buscar estructura por nombre" junto al input SMILES; usa el
    valor del campo nombre_compuesto como consulta (si está vacío,
    mensaje pidiendo completarlo).
  - Éxito: rellena `id_smiles` + mensaje neutro "Estructura cargada.
    Revísala y edítala si es necesario."
  - Fallo 404: mensaje "No se encontró una estructura para \"<nombre>\".
    Puedes buscarla en PubChem y pegar el SMILES manualmente." + link
    `https://pubchem.ncbi.nlm.nih.gov/#query=<nombre>` (target blank).
  - Fallo 502: mensaje de servicio no disponible + mismo link.
- JS nuevo `static/js/estructura_lookup.js` (?v=1), vanilla, sin deps.
- Sin dependencias nuevas; sin migraciones.

Non-goals (sellados): PubChem automático via subprocess curl (Entrega 3
opcional), httpx/http2 spike (Entrega 3 alternativa), cascada multi-
proveedor, cache de resultados.

## Tasks

- [x] T1 Feature doc + Engram mirror + todo projection (este doc)
- [x] T2 Resolver Cactus (`app_quimico/estructura_lookup.py`) + 13 tests
      con urllib mockeado (200/404/500/timeout, cuerpo ERROR, cuerpos no
      utilizables: "XYZ"/"C C"/"no es un smiles", primera línea de
      multilínea, URL-encoded del nombre, UA propio). Guard de whitespace
      alineado con clean_smiles (pysmiles parsea "C C" como 2 átomos).
- [x] T3 Endpoint `lookup_views.py` + url `compuestos/api/lookup-estructura/`
      + 9 tests (401 JSON para anónimo sin redirect HTML — sin
      @login_required, check explícito is_authenticated; 405; 400 sin
      parámetro/vacío/largo; 200 con fuente; 404/502 mapeados).
- [x] T4 Frontend `static/js/estructura_lookup.js` (?v=1) + wiring en
      `compuesto_form.html` (botón con data-lookup-url, contenedor de
      mensaje, enlace PubChem target=_blank) + 6 tests de plantilla/JS
      (incluye guard anti-voseo del copy).
- [x] T5 Suite completa verde (328 passed, era 300) + check limpio +
      makemigrations --check sin cambios + work-unit commit 43c1c59
      (Conventional Commit, descripción en español).
- [ ] T6 Push + deploy PA (operador) + validación en producción

## Evidence

(completa a medida que se ejecutan)
