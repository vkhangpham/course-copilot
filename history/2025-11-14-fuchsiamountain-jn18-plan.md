# Plan – ccopilot-jn18 (Cover resolve_dataset_root env overrides)

## Goal
`resolve_dataset_root` now lets `ExerciseAuthor` and `Explainer` load the dataset via env overrides, but there’s no regression coverage for the helper itself. Add explicit tests that assert the env vars win and the repo fallback works so future refactors keep the invariants intact.

## Steps
1. Import `resolve_dataset_root` into `tests/test_ta_roles_paths.py` so we can call it directly.
2. Add tests that set `COURSEGEN_DATASET_DIR` and `COURSEGEN_REPO_ROOT` and verify the helper resolves to the expected paths.
3. Run `pytest tests/test_ta_roles_paths.py -q` to prove the helper works as advertised.
4. Document progress here and close the bead once done.

## Progress
- 2025-11-14 12:23 UTC – Added helper tests and validated via pytest; helper now covered in `tests/test_ta_roles_paths.py`.
