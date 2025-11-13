# Plan – ccopilot-c9h6 (Portal should expose science config path)

## Goal
Expose the newly recorded `science_config_path` in portal APIs and UI so reviewers can see which evaluator config each run used without downloading manifests manually.

## Steps
1. Update `apps/portal_backend/main.py` models (`RunListItem`, `RunDetail`) and sanitization helpers to carry the science config path, populate it in `_list_runs`, and include it in run detail responses.
2. Update `frontend/lib/api.ts` types plus `RunHistory` UI (and run detail components if needed) to display the path or at least make it accessible (e.g., small badge or tooltip).
3. Extend backend/frontend tests (`tests/test_portal_backend.py`, relevant Jest/React expectations if any) and run targeted lint/tests (`pytest tests/test_portal_backend.py -q`, `npm run lint` or `pnpm lint` if available).
4. Document behavior if necessary, send Agent Mail status, close bead.

## Progress
- 2025-11-13 00:04Z – Reserved portal/backend/frontend files, announced plan via Agent Mail, drafted steps.
- 2025-11-13 00:15Z – Added `science_config_path` to portal API (backend + tests) and surfaced it in RunHistory UI; `pytest tests/test_portal_backend.py -q` and `pnpm lint` both pass.
