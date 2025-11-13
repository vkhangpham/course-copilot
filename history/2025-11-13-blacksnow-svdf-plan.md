# Plan – ccopilot-svdf (Serve scientific metrics via portal API)

## Goal
Fix the run detail "Scientific metrics (JSON)" link by adding a first-class API endpoint that serves the metrics artifact instead of pointing directly at the filesystem (which 404s).

## Steps
1. Add `/runs/{run_id}/science-metrics` to `apps/portal_backend/main.py`, resolving the manifest field safely and returning the JSON contents.
2. Update `RunDetailSection` to call this endpoint rather than building a raw path; adjust types if needed.
3. Extend `tests/test_portal_backend.py` to cover the new endpoint and run `pnpm lint` for the frontend.
4. Communicate + close bead.

## Progress
- 2025-11-13 00:27Z – Plan drafted; implementation next.
- 2025-11-13 00:33Z – Added `/runs/{id}/science-metrics` endpoint + frontend link update; `pytest tests/test_portal_backend.py -q` and `pnpm lint` both pass.
