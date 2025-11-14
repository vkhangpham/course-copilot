# Plan – ccopilot-scxu (wm-inspect repo detection should skip unrelated pyproject roots)

## Goal
`wm-inspect` now walks the current working directory upwards looking for a `pyproject.toml` and assumes the first match is the CourseGen repo. When developers run the CLI from another project that also contains `pyproject.toml`, the CLI anchors itself to that unrelated path and then fails with "World model store not found" because `outputs/world_model/state.sqlite` doesn’t exist there. We need stricter repo detection so the fallback only triggers when the parent actually looks like the CourseGen repo (e.g., contains `config/pipeline.yaml`).

## Steps
1. Reproduce: create a temp directory with only `pyproject.toml`, run `_resolve_repo_root()` from within it, and confirm it incorrectly returns that directory.
2. Update `_looks_like_repo_root` in `scripts/query_world_model.py` to require both `pyproject.toml` and another repo-specific marker (e.g., `config/pipeline.yaml`). Consider allowing multiple candidate markers so packaging still works.
3. Extend `tests/test_query_world_model.py` with coverage for the false-positive scenario and the positive case (directory containing both markers is accepted).
4. Run `pytest tests/test_query_world_model.py -q`.
5. Communicate progress via Agent Mail thread `ccopilot-scxu`, then close the bead once merged.

## Progress
- 2025-11-13 11:19 UTC – Plan drafted; reproduction + implementation pending.
- 2025-11-13 11:28 UTC – Reproduced the false positive by pointing `_search_repo_root` at a temp directory containing only `pyproject.toml`; added regression tests that assert the helper skips that case and accepts directories that also include `config/pipeline.yaml`.
- 2025-11-13 11:31 UTC – Updated `_looks_like_repo_root` to require both `pyproject.toml` and `config/pipeline.yaml`, reran `pytest tests/test_query_world_model.py -q` (20 passed).
- 2025-11-13 11:33 UTC – Closed ccopilot-scxu after notifying the team via Agent Mail; reservations released.
