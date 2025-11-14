# Plan – ccopilot-o1g (bootstrap_pipeline should override COURSEGEN_REPO_ROOT)

## Goal
Ensure `bootstrap_pipeline` always exports the repo root derived from the CLI flag (or fallback) so downstream tooling (wm-inspect, CodeAct tools) resolve paths correctly even when a caller already set `COURSEGEN_REPO_ROOT` before invoking the CLI.

## Steps
1. Audit current env export logic in `ccopilot/pipeline/bootstrap.py` and reproduce the issue (env var remains stale when `--repo-root` differs from the existing value).
2. Update bootstrap to unconditionally set `COURSEGEN_REPO_ROOT` (and any dependent paths) based on the resolved repo root, documenting rationale if needed.
3. Add/extend unit tests (likely in `tests/test_pipeline_runtime.py` or a new focused test) to cover overriding behavior.
4. Run targeted pytest suites covering pipeline/bootstrap modules.

## Status
- 2025-11-13 04:42Z – Plan drafted; beginning investigation of bootstrap env handling.
# BlackLake – Daily Plan (2025-11-13)

## Completed
- **ccopilot-o1g – bootstrap_pipeline should override COURSEGEN_REPO_ROOT when --repo-root is provided**  
  1. ✅ Reproduced path leakage by exporting `COURSEGEN_REPO_ROOT=/repo/A` and invoking the CLI with `--repo-root /repo/B`; env var stayed pinned to `/repo/A`.  
  2. ✅ Updated `ccopilot/pipeline/bootstrap.py` to always set `COURSEGEN_REPO_ROOT` to the resolved repo root argument, so CodeAct + tooling follow the active checkout.  
  3. ✅ Added regression coverage (`tests/test_pipeline_runtime.py::test_repo_root_overrides_existing_env`) and ran `pytest tests/test_pipeline_runtime.py -q`.  
  4. ✅ Communicated via Agent Mail thread `ccopilot-o1g` and closed the bead.

## Next Up
- Pick up the next reliability-focused bead (likely under ccopilot-dqc) that tightens env/config handling across orchestrator + CodeAct subsystems.
