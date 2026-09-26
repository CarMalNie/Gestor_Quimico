# Feature: p1-categoria-filtros — Datos IUPAC confiables + leyenda de categorías con familias

## Contexto / auditoría (2026-09-24)

- Bug reportado por el operador: los chips "Metales" y "Otros No Metales" no filtraban nada en la
  vista tabla (ni en el form de tarjetas, mismos choices muertos).
- Causa raíz: la leyenda se renderiza desde `CATEGORIA_CHOICES` completa (12 opciones,
  `views.py:321`), pero los datos (`app_quimico/data/detalles_elementos.py`) usan solo 10
  categorías — `'Metales'` y `'Otros No Metales'` son choices muertos sin ningún elemento.
- Auditoría IUPAC (fuentes: IUPAC Periodic Table PDF 28Nov2016; Wikipedia Group 12 / Polonium /
  Astatine / Oganesson; RSC Chemistry World): los 118 elementos son consistentes con el esquema
  didáctico IUPAC-style de 10 categorías, salvo los casos de frontera resueltos abajo.
- Directriz del operador (2026-09-24): la base de datos de elementos debe ser lo más fidedigna y
  precisa posible según fuentes oficiales y aceptadas por la ciencia de la química — esto aplica
  también a las propiedades (pesos, electronegatividades, ionizaciones, afinidades, radios).

## Decisiones del operador

1. **Filtros**: chips de familia + categorías finas juntos (opción "ambos").
   - "Metales" (familia) = Alcalinos + Alcalinos-térreos + Metales de Transición + Otros Metales +
     Lantánidos + Actínidos (**92** elementos tras mover Po; metaloides NO cuentan como metales).
   - "No metales" (familia) = No Metales + Halógenos + Gases Nobles (20 elementos).
   - Chips finos: solo las 10 categorías realmente en uso (nunca las muertas).
2. **Po**: Metaloides → **Otros Metales**, fundado en RSC ("classed as a metal") + Wikipedia
   (metal, a veces metaloide). Metaloides queda en el sexteto indiscutido B, Si, Ge, As, Sb, Te
   (6); Otros Metales 11 → 12.
3. **Superpesados (Z≥104)**: mantener categoría por posición + nota breve de honestidad en la
   descripción: las propiedades químicas aún son desconocidas para la ciencia (la data NO está
   incompleta; son predicciones). Mensaje corto, honestidad + simplicidad.
4. **Propiedades**: auditoría contra fuentes oficiales (CIAAW/IUPAC 2021 pesos atómicos; NIST
   energías de ionización y afinidades electrónicas; escala Pauling convencional; Cordero 2008
   radios covalentes). Correcciones de datos aprobadas → aplicar; disputas documentadas, no
   corregidas a ciegas.
5. Convenciones que se mantienen (documentadas en docstring de datos): grupo 3 con f-block
   completo (La–Lu / Ac–Lr); grupo 12 como Metales de Transición (convención de tabla estándar);
   At como Halógenos (posición grupo 17).

## Alcance (Entrega 1)

- T1 Quitar los 2 choices muertos de `CATEGORIA_CHOICES`; constantes `FAMILIA_METALES` /
  `FAMILIA_NO_METALES` junto al modelo; form de filtros de tarjetas usa las 10 reales. Sin
  migración (CharField choices no altera la BD).
- T2 `views.py`: leyenda = 2 chips de familia + 10 finos (familias primero).
- T3 Template (`elemento_lista.html`) + `periodic_table.js`: familias con `data-categorias`
  (separadas por "|"); matcheo del filtro contra cualquiera de las categorías del chip; chips
  finos igual que hoy. aria-pressed, hover preview y toggle intactos. Bump de cache-busting.
- T4 Datos: Po → Otros Metales en `detalles_elementos.py`; docstring con convenciones + fuentes;
  nota breve de honestidad en descripción de los 15 superpesados (Rf–Og). Actualizar
  `cargar_elementos` tests afectados; runbook: `python manage.py cargar_elementos` en PA corrige
  la DB (update_or_create sobre DetalleElemento).
- T5 Tests: leyenda sin chips muertos; familias matchean conjuntos esperados (91/20); Po en
  Otros Metales; regresión del filtro fino.
- T6 Cierre: suite completa verde, `check` + `makemigrations --check`, commits de work-unit.
- T7 (investigación, paralelo): auditoría de propiedades contra CIAAW 2021 / NIST / Pauling /
  Cordero 2008; reporte con citas; correcciones solo de valores respaldados.
- T8 Correcciones de propiedades surgidas de T7 (si las hay, con sus fuentes).

## Fuera de alcance

- Entrega 2 PubChem / niceities tabla / DRF (backlog separado).

## Estado

- [x] T1 — choices muertos fuera + FAMILIA_METALES/FAMILIA_NO_METALES (models.py 25-55; forms.py
  consume CATEGORIA_CHOICES, no requirió edición). NOTA: la premisa "sin migración" era falsa —
  Django trackea choices en el estado de migraciones → migración state-only 0011 (aprobada por el
  operador vía writer).
- [x] T2 — views.py 318-337: context['leyenda'] = 2 familias + 10 finas (reemplaza 'categorias').
- [x] T3 — elemento_lista.html (pt-chip-familia + data-categorias; JS ?v=3) + periodic_table.js
  (matcheo por conjunto; toggle/aria-pressed/hover intactos).
- [x] T4 — Po → Otros Metales; docstring de convenciones con fuentes; nota de honestidad en los 15
  superpesados (Rf–Og), una vez cada uno.
- [x] T5 — tests: leyenda sin chips muertos; familias 92 metales / 20 no metales / 6 metaloides
  (el 91 del plan era previo al cambio de Po; test aserta 92 con el porqué documentado); Po en
  Otros Metales; regresión fina.
- [x] T6 — verificación independiente 7/7 PASS (270 tests en 266.69s; check + makemigrations
  --check + node --check limpios).
- [x] T7 — Auditoría de propiedades (parent inline, web): pesos CIAAW 2021 84/84 match; EN Pauling
  94/95 (fix Am 1.13→1.30); IE NIST 100/118 (fixes Tc 702→686.9, At 890→899.0, No 634→639); EA
  magnitudes correctas en convención ΔE negativa (5 en disputa de fuentes: Mo, In, Tl, Po, At — no
  corregir a ciegas) + ~30 faltantes con valor medido; radio covalente usa tabla vieja en Å →
  reemplazar por Cordero 2008 en pm; 34 elementos sin peso estándar → presentación [nº masa];
  refresco CIAAW 2024 Gd/Lu/Zr.
- [x] T8 — correcciones aplicadas por writer (suite 283 passed; migración 0012 state-only):
  Zr 91.224→91.222 (CIAAW 2024); Am EN 1.13→1.30; IE Tc 686.9 / At 899.0 / No 639 (NIST);
  radios covalentes → Cordero 2008 en pm (95 elementos; Bk/Cf → None: Cordero no los cubre,
  decisión honesta aprobada por el parent) + migración campo max_digits 6, límites 28–350 pm;
  21 afinidades medidas completadas (ΔE negativa); 34 elementos sin peso estándar se muestran
  [nº masa] (helper peso_atomico_para_mostrar + ELEMENTOS_SIN_PESO_ESTANDAR); EA label con
  aclaración ΔE; placeholder del form corregido a "pm" (fix inline del parent).
  VERIFICACIÓN INDEPENDIENTE: 6/6 PASS (283 tests; diffs exactos vs HEAD: solo EN 1, IE 3,
  EA 21 fills, radio 93 sobrescritos + Ne/Ar nuevos + Bk/Cf a None; descriptores/categorías
  byte-idénticos). Commit de T8: 586e707.
- [x] T9 — cierre: suite verde, commits c466223 / 3c13863 / edf3007 (T1-T6) + 586e707 (T8),
  árbol limpio.
- [x] T11 — verificación independiente 7/7 PASS (suite 297 passed): diffs exactos (solo los 7
  elementos renombrados), labels sin 'Todos los', CSS ?v=4 con slugs estilizados en ambos temas,
  filtro de familias intacto (92/20/exacto), seed idempotente confirma la adopción.
  Commits: f38fd26 (docs), b96fd0f (feat).
- [x] (historia) El operador corrigió el enfoque: NO inventar agrupaciones; usar
  
      (cerrada como parte de T10/T11: renombre ejecutado y validado en
      producción; commits e8209af plan, f4dc5b8 cierre con verificación
      independiente; feature COMPLETA T1-T11)
- [x] T10 — feedback del operador tras revisión local: (a) select "Por Categoría" de tarjetas
  ahora ofrece las familias ("Metales (todos: 92)" / "No metales (todos: 20)", sentinels
  familia_metales/familia_no_metales, server-side __in=FAMILIA_*, else __exact); (b) leyenda de
  tabla: chips de familia renombrados "Todos los metales"/"Todos los no metales" con estilo
  propio (.pt-chip-familia dashed+uppercase, paleta por tema). Causa raíz del "duplicado":
  slugify colisionaba el slug de familia "No metales" con el fino "No Metales" (misma clase
  de color). Suite 292 passed (+9); verificación independiente 6/6 PASS.

## Commits de work-unit

- (T10) feat(elementos): familias en el filtro de tarjetas + labels de familia desduplicados

- c466223 feat(elementos): reclasificar Po + convenciones + nota superpesados + migración 0011
- 3c13863 feat(elementos): leyenda con filtros de familia y chips finos (views/template/JS/tests)
- edf3007 chore(tasks): cierre p1-categoria-filtros T1-T6
- 586e707 feat(elementos): datos corregidos contra fuentes oficiales (T8 auditoría)

- feat(elementos): reclasificar Po + convenciones + nota superpesados + migración 0011
- feat(elementos): leyenda con filtros de familia y chips finos (views/template/JS/tests)
- chore(tasks): cierre p1-categoria-filtros T1-T6
