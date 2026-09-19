# Feature: p1-frontend-polish

Light frontend pass per the operator-approved backlog (obs #417 items 4a,
4b, 4d), followed by a separate dark-theme task (4c) once this lands.

## Tasks

1. [ ] Password visibility toggle (eye button, right side of the input,
   show/hide alternation) in login and registro forms. No external libs —
   the Font Awesome 5 CDN already loaded in base.html provides
   fa-eye/fa-eye-slash. Reusable approach (partial/template include).
2. [x] Responsive home: the 2-3 CTAs stack cleanly and stay centered on
   mobile (BS grid utility pattern instead of fixed `me-3` spacing).
3. [x] CI actions bump: actions/checkout@v4→v5 and
   actions/setup-python@v5→v6 in .github/workflows/ci.yml (clears the
   Node 20 deprecation warning).
4. [x] Verification: suite green (no behavior change expected — template/
   workflow-only), checks, work-unit commits, push per operator decision,
   PA deploy (collectstatic only if static changes affect the cache).

## Notes from exploration (2026-09-19)

- login.html renders `{{ form.password|as_crispy_field }}`; registro.html
  renders the whole form with `{{ form|crispy }}` — needs per-field
  rendering for the two password fields.
- perfil_personal.html has no password fields (grep empty) — toggle scope
  is login + registro only.
- home CTAs: `btn btn-success btn-lg me-3` inside a text-center container
  — fixed horizontal spacing breaks on mobile (reported by operator).
- base.html loads Bootstrap bundle (auto-hosted) + Font Awesome 5 CDN —
  eye icons available via fa-eye/fa-eye-slash without new dependencies.
- Theme phase (separate, later): styles.css has 8 `!important` rules
  (navbar/footer/body-bg) that will need variable-based restructuring for
  `data-bs-theme="dark"`.

## Evidence

- (to be filled per work-unit commit)
- 2026-09-19 1c4384b feat(frontend): toggle ojo (partial reutilizable +
  login + registro desglosado), 1a1d9c2 fix(frontend): hero responsive +
  alineación navbar (Cerrrar Sesión, reporte del operador), 6e43e0c
  ci(actions): checkout v5 / setup-python v6. Suite 56 passed, check
  limpio, render structural check (ids únicos, ARIA, errores crispy).
- Punto 2 (tema oscuro) CERRADO en el mismo registro: commits (feat
  frontend tema oscuro BS 5.3: styles.css reestructurado !important 8->2,
  partial theme_toggle con persistencia localStorage, script pre-paint
  anti-flash, bg-light/bg-white -> bg-body-tertiary/bg-body en 12
  templates, sweep final 0 matches). Suite 56 passed, check limpio,
  contraste WCAG verificado (navbar 7.74:1, dark body 11.85:1).
- CI del punto 1 CONFIRMADO por el operador: Success con checkout@v5 /
  setup-python@v6, warning Node 20 desaparecido (queda la notice de
  Ubuntu 26, informativa).
