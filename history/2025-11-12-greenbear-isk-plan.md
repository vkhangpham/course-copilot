# Plan – ccopilot-isk (CodeAct world model tools should anchor store path)

## Goal
`apps/codeact/tools/world_model.py` sets `DEFAULT_STORE = Path("outputs/world_model/state.sqlite")`, which breaks CodeAct helper calls whenever the working directory is not the repo root (e.g., when invoked from orchestrator processes). Align it with the recently fixed query CLI by anchoring the default path to the repository root (or fallback to env var) so tool calls always find the store.

## Steps
1. Compute `PROJECT_ROOT = Path(__file__).resolve().parents[2]` (since the file lives under `apps/`) and set `DEFAULT_STORE` to `(PROJECT_ROOT / "outputs/world_model/state.sqlite").resolve()`.
2. Update any tests referencing the old default (e.g., codeact/world model tool tests) to expect the anchored path or rely on env overrides.
3. Run `pytest tests/test_codeact_world_model_tools.py -q` (plus related slices if needed).
4. Update plan log, broadcast via Agent Mail, and close the bead.

## Progress
- 2025-11-12 11:40Z – GreenBear opened ccopilot-isk, reserved the CodeAct tool/test files, and started anchoring the default world-model store path.
- 2025-11-12 11:41Z – Anchored the CodeAct default store to the repo root, added a regression in `tests/test_codeact_world_model_tools.py`, and ran `pytest tests/test_codeact_world_model_tools.py -q` → 10 passed.
