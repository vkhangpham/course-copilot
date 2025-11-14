# Plan – ccopilot-tc1 (CodeAct world model tools should honor COURSEGEN_REPO_ROOT)

## Goal
`apps/codeact/tools/world_model.py` currently resolves `DEFAULT_STORE` once at import time based on the package path. When the PoC runs outside the repo (pip install or external working dir) the tools still point at `<site-packages>/outputs/...` even if `COURSEGEN_REPO_ROOT` is set. Align the CodeAct tools with the CLI behavior by resolving the store relative to the env override and add regression coverage.

## Steps
1. Inspect existing env handling (`DEFAULT_STORE`, `_adapter`) and document the gap (COURSEGEN_REPO_ROOT ignored, WORLD_MODEL_STORE used only if explicitly set).
2. Update the module to compute the default store path at runtime using COURSEGEN_REPO_ROOT when provided, falling back to the current project-relative path, and ensure `_adapter` uses the updated helper.
3. Extend `tests/test_codeact_world_model_tools.py` with a test that sets `COURSEGEN_REPO_ROOT` to a temp repo and verifies `fetch_concepts` resolves correctly (and still honors WORLD_MODEL_STORE env).
4. Run `pytest tests/test_codeact_world_model_tools.py -q`, record results, and notify via Agent Mail thread `ccopilot-tc1`.

## Progress
- 2025-11-13 01:47Z – Plan drafted; no code changes yet.
- 2025-11-13 01:52Z – `_adapter` now resolves defaults via `COURSEGEN_REPO_ROOT`/`WORLD_MODEL_STORE`, added runtime repo-root test, and reran `pytest tests/test_codeact_world_model_tools.py -q` (13 passed).
