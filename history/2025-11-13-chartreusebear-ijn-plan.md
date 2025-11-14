# Plan – ccopilot-ijn (Notebook publisher should run even when recursion ablated)

## Goal
Notebook exports currently depend on `ctx.ablations.allow_recursion` because `_notebook_exports_enabled()` returns that flag. Running `coursegen-poc --ablations no_recursion` (intended to disable the Teacher RLM’s recursive calls) inadvertently skips notebook publishing entirely. Update the orchestrator so notebook exports are controlled solely by the notebook config (and existing CLI flags), not the recursion ablation. Add tests proving exports still run when recursion is disabled.

## Steps
1. Identify the gating logic (likely in `apps/orchestrator/teacher.py` or `notebook_publisher.py`) that ties notebook exports to `allow_recursion`.
2. Adjust the orchestrator to base the decision on notebook config (e.g., `ctx.config.notebook.auto_create` or presence of slug) instead of recursion.
3. Add regression tests in `tests/test_pipeline_runtime.py` (or a new orchestrator test) verifying notebook exports still occur when `no_recursion` is set.
4. Run targeted pytest (pipeline runtime + any new tests), update history, and notify via Agent Mail thread `ccopilot-ijn`.

## Progress
- 2025-11-13 02:46Z – Plan drafted; analyzing `_notebook_exports_enabled` next.
- 2025-11-13 02:55Z – Updated `TeacherOrchestrator` so notebook exports depend on notebook config (slug present) rather than `allow_recursion`, enabling CodeAct hops even when recursion is ablated.
- 2025-11-13 02:57Z – Replaced the pipeline regression with `test_recursion_ablation_still_exports_notebook`; `pytest tests/test_pipeline_runtime.py -k still_exports_notebook -q` passes.
