# ccopilot-rz1 · Notebook API mock + offline export harness (2025-11-12)

## Objective
Prepare for Phase F (Open Notebook export) by ensuring we can exercise `push_notebook_section` end-to-end without a live API. Deliverables:
1. Lightweight FastAPI mock server that emulates the endpoints we need (`POST /api/notebooks/{slug}/notes` etc.) and can run inside pytest via `TestClient`.
2. Integration tests covering both the online path (mock server) and offline exporter/mirroring paths.
3. Documentation updates so operators know how to configure `OPEN_NOTEBOOK_EXPORT_DIR` / `OPEN_NOTEBOOK_EXPORT_MIRROR` and how to run the mock in dev.

## Tasks
1. **Mock server + client hook**
   - Add a helper under `tests/mocks/` (or `apps/portal_backend/tests/`) that spins up a FastAPI app with in-memory storage.
   - Expose fixtures for pytest so tests can easily obtain the base URL + token.

2. **Tool updates**
   - Refine `apps/codeact/tools/open_notebook.py` to accept an optional `session` (for dependency injection) and to log the note payload returned by the API.
   - Ensure mirrored exports include metadata (e.g., request id) so we can correlate offline + online behavior.

3. **Testing**
   - New file `tests/test_open_notebook_tools.py` that covers:
     - API path: pushing a section to the mock server returns 200 and writes the note entry.
     - Offline path: missing API base but export dir set results in JSONL append.
     - Mirroring path: API call plus local JSONL when `OPEN_NOTEBOOK_EXPORT_MIRROR=1`.
     - Error handling: missing slug/API base raises the documented ValueErrors.

4. **Docs**
   - Update README + docs/PLAN.md Phase F section with a short "Mocking Open Notebook" snippet and env variable reference.

5. **Coordination**
   - No current reservations on `apps/codeact/tools/open_notebook.py`; I’ll grab them before editing and notify the team via the standup thread.
   - RedDog’s `ccopilot-hxt` shouldn’t conflict, but we’ll sync if their student-loop changes touch the same files.

## Dependencies
- Blocked by none (this is prep work for ccopilot-5fr but can proceed in parallel with ccopilot-hxt).

– ChartreuseCastle
