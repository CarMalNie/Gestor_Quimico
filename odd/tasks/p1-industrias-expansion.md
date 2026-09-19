# Feature: p1-industrias-expansion

Expand the seeded industrial catalog per the operator-approved proposal:
8 new industries with 26 applications, on top of the cátedra's
5 industries / 10 applications already seeded by migration 0007.
Totals after this migration: 13 industrias, 36 aplicaciones. Same
policy as 0007: compounds are NOT seeded (operator creates them manually
through the web). All data must be visible through the existing web CRUD
(/industrias/ and /aplicaciones/ list views, login required).

## Approved data (operator decision 2026-09-19)

Industrias (8): Agroquímica, Cosmética e Higiene, Construcción, Automotriz,
Textil, Pinturas y Recubrimientos, Cuidado del Hogar, Laboratorio y Docencia.

Aplicaciones (26, nombre_uso → industria):
- Fertilización Nitrogenada → Agroquímica
- Control de Malezas → Agroquímica
- Ajuste de pH de Suelos → Agroquímica
- Fungicida Foliar → Agroquímica
- Ajuste de pH de Cosméticos → Cosmética e Higiene
- Conservación de Formulaciones → Cosmética e Higiene
- Antitranspirantes → Cosmética e Higiene
- Exfoliación Química → Cosmética e Higiene
- Acelerante de Hormigón → Construcción
- Limpieza de Superficies de Obra → Construcción
- Fabricación de Vidrio → Construcción
- Electrolito de Baterías → Automotriz
- Refrigeración de Motores → Automotriz
- Limpiador de Frenos → Automotriz
- Blanqueo de Fibras → Textil
- Fijación de Tintes → Textil
- Neutralización de Baños de Tintura → Textil
- Pigmentación Blanca → Pinturas y Recubrimientos
- Disolución de Resinas → Pinturas y Recubrimientos
- Desengrasado Metálico → Pinturas y Recubrimientos
- Desinfección Doméstica → Cuidado del Hogar
- Removedor de Sarro → Cuidado del Hogar
- Limpieza Multiusos → Cuidado del Hogar
- Preparación de Reactivos → Laboratorio y Docencia
- Estandarización de Soluciones → Laboratorio y Docencia
- Indicadores de pH → Laboratorio y Docencia

## Tasks

1. [x] Data migration 0008 (idempotent get_or_create, reverse by name),
   next free number after 0007.
2. [x] Tests: total counts after migration (13 industrias, 36 aplicaciones),
   FK mapping spot checks.
3. [ ] Full suite green + commits (work-unit), push per operator decision.

## Evidence

- (to be filled per work-unit commit)
- 2026-09-19 26d8bab feat(seed): expansión del catálogo industrial (migración
  0008: 8 industrias + 26 aplicaciones, totals 13/36 + tests table-driven).
  Resolución humana: Option 1 — lista enumerada es autoritativa (26
  aplicaciones; el anuncio "24" era un error de cuenta mío, la lista que el
  operador aprobó tenía 26). Suite: 53 passed, check y makemigrations
  --check limpios (validación del writer; readback del parent).
