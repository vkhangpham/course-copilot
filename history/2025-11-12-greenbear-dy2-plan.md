# Plan – ccopilot-dy2 (Add tests for COURSEGEN_REPO_ROOT override)

## Goal
`scripts/query_world_model.py` now honors `COURSEGEN_REPO_ROOT`, but there’s no regression test ensuring the env override actually rewires `DEFAULT_STORE`. Add coverage that reloads the module under different env settings so future refactors don’t break the CLI in embedded contexts.

## Steps
1. Add a test in `tests/test_query_world_model.py` that sets `COURSEGEN_REPO_ROOT` to a temp path, reloads `scripts.query_world_model`, and asserts `DEFAULT_STORE` points to the override.
2. Ensure the test restores the original module/env after running (use `importlib.reload`).
3. Run `pytest tests/test_query_world_model.py -q`.
4. Update plan + notify via Agent Mail.

## Progress
- 2025-11-12 11:52Z – Requested file access from BlueCreek (current reservation holder) before adding the env override test.
- 2025-11-12 11:54Z – Found existing regression coverage (`tests/test_query_world_model.py::test_query_world_model_repo_override` / `test_query_world_model_store_env_override`) already exercises `COURSEGEN_REPO_ROOT`; ran `pytest tests/test_query_world_model.py -q` → 13 passed. No additional code changes needed.
- 2025-11-12 12:16Z – ChartreuseBear re-seeded dataset fixtures under a fake repo root, added `COURSEGEN_REPO_ROOT` regression tests to `tests/test_codeact_data.py`, and ran `pytest tests/test_codeact_data.py -q` (15 passed).
