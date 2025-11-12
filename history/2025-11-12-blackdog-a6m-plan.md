# Plan – ccopilot-a6m (2025-11-12)

## Context
Audit from `history/2025-11-12-orangeMountain-plan-audit.md` flagged that our ablation toggles (`no_world_model`, `no_students`, `no_recursion`) do not actually gate their respective subsystems. We just picked up **ccopilot-a6m** to harden that behavior while keeping tests in sync.

## Tasks / Status
1. ☑ **Recon** – traced the ablation plumbing in `TeacherOrchestrator` and CLI helpers. Gaps: WM highlight artifacts still emit even when `use_world_model` is false; notebook exports run regardless of recursion/world-model flags; provenance/manifest never record that subsystems were skipped.
2. ☑ **Implementation** – hardened `TeacherOrchestrator` so WM highlights/teacher loop/notebook exports all respect the relevant ablations (skip highlight artifact + teacher loop when disabled, gate notebook exports on recursion, short-circuit CodeAct helpers).
3. ☑ **Tests** – added pipeline regression tests for `no_world_model` and `no_recursion` plus a unit test covering clients without `ensure_notebook()`. Confirmed locally with `pytest tests/test_pipeline_runtime.py tests/test_cli_run_poc.py tests/test_orchestrator_codeact.py -q`.
4. ☑ **Docs & comms** – ablation behavior documented in this plan + AGENT mail; bead ready to close after sharing status update.

Will update this file inline as each step completes.
