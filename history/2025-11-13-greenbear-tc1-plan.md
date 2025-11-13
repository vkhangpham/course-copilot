# Plan – ccopilot-tc1 (CodeAct world model tools should honor COURSEGEN_REPO_ROOT)

## Goal
`scripts/query_world_model.py` respects `COURSEGEN_REPO_ROOT`, but `apps/codeact/tools/world_model.py` still hardcodes the package-relative repo root (parents[3]). When the package is installed elsewhere, the default store path points inside site-packages and the tools can’t find `outputs/world_model/state.sqlite`. We need to mirror the CLI behavior: honor `COURSEGEN_REPO_ROOT` (and continue to fall back to parents[3]) so the CodeAct helpers work in non-repo environments.

## Steps
1. Update `apps/codeact/tools/world_model.py` to resolve `PROJECT_ROOT` via the env var (with fallback), similar to `scripts/query_world_model.py`.
2. Add unit coverage in `tests/test_codeact_world_model_tools.py` ensuring the default store path updates when `COURSEGEN_REPO_ROOT` is set.
3. Run `pytest tests/test_codeact_world_model_tools.py -q`.
4. Update plan + notify via Agent Mail.

## Progress
- 2025-11-13 01:46Z – Reserved CodeAct world-model files, plan to mirror the CLI env override before adding regression tests.
- 2025-11-13 01:48Z – Added COURSEGEN_REPO_ROOT-aware project root resolution plus regression tests; `pytest tests/test_codeact_world_model_tools.py -q` → 12 passed.
