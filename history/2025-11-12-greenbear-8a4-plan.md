# Plan – ccopilot-8a4 (wm-inspect default path should be repo-anchored)

## Goal
`scripts/query_world_model.py` currently sets `DEFAULT_STORE = Path("outputs/world_model/state.sqlite")`, which is relative to the current working directory. Running `wm-inspect` from outside the repo fails even when the store exists (e.g., `wm-inspect timeline` from a parent dir). Anchor the default to the repository root so the CLI works regardless of cwd, and keep the tests in sync.

## Steps
1. Compute `PROJECT_ROOT = Path(__file__).resolve().parents[1]` in `scripts/query_world_model.py` and set `DEFAULT_STORE` to `PROJECT_ROOT / "outputs/world_model/state.sqlite"`.
2. Update `tests/test_query_world_model.py` to expect the anchored path.
3. Run `pytest tests/test_query_world_model.py -q`.
4. Update plan log, notify via Agent Mail, and close the bead.

## Progress
- 2025-11-12 11:35Z – GreenBear opened ccopilot-8a4, reserved the query CLI/test files, and is anchoring the default store path to the repo root.
- 2025-11-12 11:37Z – Anchored `DEFAULT_STORE` to the repo root and updated the regression test; `pytest tests/test_query_world_model.py -q` → 11 passed.
