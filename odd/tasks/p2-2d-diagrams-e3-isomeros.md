# Feature: p2-2d-diagrams-e3-isomeros — Entrega 3: selector de isómeros por fórmula

Sealed design (2026-09-25/26, decisiones del operador):
- Solución robusta elegida sobre el "parche" del diccionario ES→EN:
  la búsqueda usa la **fórmula molecular** (campo obligatorio del form,
  independiente del idioma del nombre) y el **usuario elige** su
  estructura entre los isómeros con nombre — la decisión química queda
  en el humano, nunca en un resolver arbitrario.
- Traducción por IA descartada: no determinista, riesgo de alucinación
  química, y el diseño por fórmula la vuelve innecesaria.
- Fallback manual: link a PubChem precargado **por fórmula** (universal;
  en PubChem el usuario ve la misma lista de isómeros y elige a mano).

## Evidencia que sella el diseño

- PubChem bloquea clientes Python HTTP/1.1 (503 fingerprint, verificado
  en PA y local) PERO **httpx con HTTP/2 pasa limpio**: spike verificado
  local Y en producción PA (operador 05:12): `fastformula/C2H6O/property/
  CanonicalSMILES,IUPACName` → 200 HTTP/2 con isómeros {CID, SMILES,
  IUPACName} (ethanol CCO, methoxymethane COC, isotopólogos...).
- httpx[http2]==0.28.1 instalado en venv PA (temporal para el spike) y
  local; la implementación lo pinneará en requirements.txt (decisión de
  dependencia formal, como django-otp).
- Cactus (Entrega 2, lookup por nombre) queda en el backend con sus
  tests: sigue siendo útil para nombres en inglés; la UI cambia a
  fórmula como único flujo del botón.

## Scope (Entrega 3)

- Cliente `app_quimico/pubchem_lookup.py`: `buscar_isomeros(formula)` via
  httpx (http2=True, timeout ~8s), parseo defensivo de campos
  (CanonicalSMILES|ConnectivitySMILES|SMILES), **dedupe por SMILES**
  conservando el primer IUPACName (el más común) y cap de ~10 candidatos.
- Endpoint `GET /compuestos/api/lookup-isomeros/?formula=<f>` (login):
  200 `{formula, candidatos: [{nombre, smiles}]}` / 400 fórmula inválida
  / 401 anónimo JSON / 404 sin resultados / 405 método / 502 servicio.
- Frontend: botón único "🔍 Buscar estructura (por fórmula)" en la
  sección 2D plegada — usa `id_formula_compuesto`:
  - 1 solo isómero → rellena el SMILES directo + mensaje de éxito.
  - N isómeros → lista de opciones clickeables (nombre + SMILES
    visibles); al elegir una, se rellena el campo.
  - 404/502 → mensaje + link PubChem precargado **con la fórmula**.
- `estructura_lookup.js` reescrito (cache-bust ?v=2), español neutro.
- requirements.txt: `httpx[http2]==0.28.1` pinneado. Sin migraciones.

Non-goals: diccionario ES→EN (descartado como parche), traducción IA,
subprocess curl (documentado en Entram, no necesario), paginación de
listas largas (cap simple + fallback manual).

## Tasks

- [x] T1 Feature doc + Engram mirror + todo projection (este doc)
- [x] T2 Cliente PubChem fastformula (`app_quimico/pubchem_lookup.py`) +
      9 tests httpx mockeados (dedupe por SMILES conserva primer
      IUPACName, cap 10, campos SMILES defensivos, 404/503/timeout/JSON
      inesperado → PubChemNoDisponible, PropertyTable vacío →
      no_encontrado).
- [x] T3 Endpoint `lookup_isomeros` + url + 9 tests (contrato completo).
- [x] T4 Frontend JS reescrito (?v=2): botón por fórmula, lista de
      candidatos list-group clickeables, relleno directo si hay 1,
      fallback por fórmula; 8 tests de plantilla/JS.
- [x] T5 requirements.txt pin `httpx[http2]==0.28.1` + suite 348 passed
      (era 328) + check limpio + commit 7f88dc6.
- [x] T6 Validación local del operador → push → PA (pip install -r
      requirements.txt + collectstatic + Reload) → validación producción
      10/10 (2026-09-26; CI verde 8b21705; hallazgo documentado:
      fastformula usa fórmula plana Hill — K4[Fe(CN)6] → 404,
      C6FeK4N6 → lista de candidatos).
- [x] T7 Feedback del operador (producción): el enlace manual a PubChem
      también debe aparecer junto a la LISTA de isómeros (no solo en
      404/502) — el compuesto puede estar fuera del cap o sin match por
      fórmula. Commit f036e41: copy "¿No se encuentra? Abrir la búsqueda
      en PubChem ↗" en la plantilla (universal), JS lo muestra junto a
      la lista, ?v=2→?v=3, 2 tests nuevos (10 passed módulo).

## Evidence

(completa a medida que se ejecutan)
