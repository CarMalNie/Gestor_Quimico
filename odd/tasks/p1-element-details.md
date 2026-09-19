# Feature: p1-element-details

Complete the chemical element database per the cátedra Word document
("Lista Elemento - Compuestos - Ind y Apli.docx"): full detail rows for all
118 elements plus industry/application seed data. Compounds are deliberately
NOT seeded — the operator will create them manually via the web with his own
account (exercises the P0 ownership feature).

## Context

- Key discovery: the model layer already complies with the cátedra spec.
  `DetalleElemento` (1:1 with `ElementoQuimico`) already has grupo, período,
  categoría, electronegatividad, afinidad electrónica, energía de ionización,
  radio covalente and descripción. Templates already render them. Only DATA
  was missing (`detalles_elementos` table empty).
- Reference data source: `Lista Elemento - Compuestos - Ind y Apli.docx`
  (Tabla 0: 10 elements with grupo/período/categoría; Tabla 1: 10 elements
  with electronegatividad/afinidad/ionización/radio covalente). Our dataset
  must reproduce those 10 reference values and extend to the remaining 108
  with standard published values (CRC/standard tables), adjusted to the
  sign/format conventions the model expects.
- Validator bounds to respect while compiling:
  - electronegatividad: [0.70, 4.00] (noble gases / no-value → NULL)
  - afinidad_electronica: [-348.00, -0.0001] strictly negative, kJ/mol,
    NULL where unavailable
  - energia_de_ionizacion: [382.70, 2372.30] kJ/mol — CAUTION: CRC lists
    Cs = 375.70; if real data conflicts, prefer fixing the validator bound
    over falsifying data (decide with explicit evidence)
  - radio_covalente: [0.32, 2.98] Å

## Tasks

1. [x] Compile `app_quimico/data/detalles_elementos.py`: 118 rows
   (simbolo, grupo, período, categoría, electronegatividad, afinidad,
   ionización, radio, descripción corta en español), validated against the
   Word tables and model validators via a standalone validation script.
2. [x] Extend `cargar_elementos` to upsert `DetalleElemento` (idempotent,
   keeps user edits to other fields).
3. [x] Data migration seeding 5 industrias + 10 aplicaciones (Tabla 2,
   minus compounds). Idempotent via get_or_create.
4. [x] Tests: command loads/updates detalles; migration seeds base rows;
   dataset values fit validator bounds.
5. [x] Full suite + check; work-unit commits; README touch if warranted.

## Evidence

- 2026-09-19 ed0f084 feat(data): detalles físicos de los 118 elementos y cotas
  de validators reales (dataset + validators + migration 0006 + comando
  extendido + tests de carga). Suite verde: 50 passed.
- 2026-09-19 ab01ea9 feat(seed): industrias y aplicaciones de la cátedra por
  data migration (0007 + tests + fixtures get_or_create). Suite verde: 50 passed.
- Resolución humana: Option A/A1 — fixtures reutilizan la industria sembrada
  por la collation acento-insensible de MySQL (utf8mb4_0900_ai_ci).
- 2026-09-19 9e097c6 chore(tasks): registro de la feature.
- 2026-09-19 ASSESS nativo: review nativa UNAVAILABLE para este candidato
  (START baseRef falla con schema-incompatible; par fachada gentle-pi 3.2.1
  vs CLI gentle-ai 3.3.0) -> riesgo tratado como alto, plan risk-gated:
  writer self-verification + verificador independiente. Verificador
  gentle-ai-verify: 7/7 PASS (suite 50 passed, check y makemigrations
  --check limpios, readback estructural de 0006/0007, sin secretos ni
  mojibake). Los 10 valores de referencia del docx cátedra se validaron
  directo contra el Word al compilar el dataset (misma sesión).
