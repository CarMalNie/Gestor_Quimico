# Feature: P1 R3 Fixes — gestor_quimico

Goal: close the five informative findings from the native RDD review of p0-hardening
(weight cache staleness, cascade JS empty-map edge case, detail/owner test gap,
zero subscript handling) while keeping the Django monolith as the professional
baseline before the DRF phase.

Operator decisions (2026-09-17, resumed session):
- Strategy: monolith Django professionalization first; CI GitHub Actions added now
  (cheap, high recruiter visibility, protects all later work); Docker deferred;
  DRF phase last, presented as evolution with real evidence.
- Scope of this feature: the R3 review findings. Backend/frontend corrective P1
  items (logout POST, {e} leak, pagination, etc.) go in a follow-up feature.
- No commits or pushes unless the operator explicitly asks.

## Tasks

- [x] T1 Weight cache invalidation: `invalidar_cache_pesos()` in utils.py +
      post_save/post_delete signals on ElementoQuimico (app_quimico/signals.py,
      wired in apps.py ready()). Two DB-backed tests (update + delete paths) and
      an autouse fixture keeping the module-global cache from leaking across tests.
      (11 tests in tests.py green.)
- [x] T2 Cascade JS empty-map edge case: fail-open — an empty/missing/invalid
      industry map no longer hides every application option silently; server-side
      clean() validation remains the guard. Syntax verified with node --check.
- [x] T3 Detail/owner test gap: positive ownership test added
      (test_owner_can_view_own_compound_detail: 200 + content). 11 tests green.
- [x] T4 Zero subscript: tokenizer rejects all-zero digit runs (H0, Fe00, Ca(OH)0)
      with a clear Spanish message; defensive invariant in the stack loop upgraded
      from silent skip to raise. 'H10' still valid (zero inside a digit run).
      4 new parser tests; 17 calculator tests green.
- [x] T5 Final verification: full suite 31 passed, manage.py check clean.

## Decisions / notes

- Cache invalidation strategy: invalidate-on-change (signals) instead of TTL —
  the DB is the single source of truth and invalidation is exact, no staleness
  window; cost is one reload per element edit (rare operation).
- Cascade JS fails open on unusable data rather than hiding all options; the
  form-level clean() cross-validation already rejects cross-industry mismatches,
  so fail-open trades silent UI emptiness for an explicit server-side error.
- Browser behavior of the cascade fix verified manually by the operator (JS logic
  has no Python unit-test path).

## Evidence

- Commits: 8ca70ed fix(review) (hallazgos R3) y 963a43e chore(tasks) (registro).
