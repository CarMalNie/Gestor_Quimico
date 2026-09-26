# Feature: p2-2d-diagrams-e4-modal-zoom — Diagrama 2D ampliado en modal

Sealed design (2026-09-26, propuesto por el operador durante la validación
de la Entrega 3): la miniatura del diagrama en tarjetas/detalle es chica
por espacio; un modal de Bootstrap re-dibuja el mismo SMILES a tamaño
grande (SVG nítido, no estiramiento). Entrega 1..3 permanecen intactas.

Comportamiento sellado:
- Las tarjetas siguen mostrando su diagrama miniatura tal cual hoy.
- Click sobre el diagrama abre el modal (cursor zoom-in como pista) +
  botón "Ampliar" visible junto al diagrama (accesibilidad).
- El modal re-renderiza el SVG a ≈600×450 con el mismo SMILES (nítido,
  no estiramiento de imagen); mismo fondo claro fijo (legible en ambos
  temas, decisión de la Entrega 1).
- Cierre: X, ESC, click fuera (modal nativo BS5, cero JS custom de modal).
- Solo para compuestos con SMILES: sin estructura, todo queda igual.
- En lista Y detalle.
- Caveat a documentar (observación del operador con K4[Fe(CN)6]):
  SmilesDrawer dibuja por símbolo elemental — el carbono de un ligando
  cianuro se ve como un C orgánico corriente (correcto: es un carbono
  con valencia cumplida); si el SMILES trae [C-]#N con carga, el drawer
  muestra la etiqueta de carga.

Non-goals: zoom/pan con rueda o arrastre (descartado en Entrega 1),
descarga de imagen, tamaño configurable por el usuario.

## Tasks

- [ ] T1 Feature doc + Engram mirror + todo projection (este doc)
- [ ] T2 JS: re-dibujo en el modal (aprovechar el core de smiles_render.js)
      + tests (aserciones de función/contrato)
- [ ] T3 Templates: tarjeta y detalle ganan disparador (click + botón)
      + modal base + tests de plantilla
- [ ] T4 Suite completa verde + work-unit commit (español)
- [ ] T5 Validación local operador → push → PA (collectstatic + Reload)
      → validación producción

## Evidence

(completa a medida que se ejecutan)
