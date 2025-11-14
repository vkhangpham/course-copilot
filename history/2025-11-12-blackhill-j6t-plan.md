# ccopilot-j6t · Orchestrator ablation enforcement plan

## Background
`ccopilot/cli/run_poc.py` supports `--ablations` (no_world_model, no_students, no_recursion), but the runtime ignores those toggles: highlights still query the world model, student graders still run, and notebook export always triggers recursion. Need to honor the flags so PoC runs can demonstrate subsystem isolation per PLAN §4.

## Tasks
1. **World-model ablation** ✅
   - Manifest now records `world_model_store_exists=False` when `no_world_model` is set so downstream tooling sees the ablation.
2. **Student ablation** ✅ (already present)
   - `_evaluate_artifacts` already short-circuits and CLI reflects the status; no code changes required.
3. **Recursion ablation** ✅
   - `_run_codeact_program` now logs and returns early when recursion is disabled, so CodeAct/Teacher RLM hooks are skipped cleanly.
4. **Tests** ✅
   - Added regression coverage in `tests/test_orchestrator_codeact.py::test_recursion_ablation_skips_codeact` and expanded `tests/test_pipeline_runtime.py::test_dataset_highlights_present_when_world_model_disabled` to assert the manifest flag.

## Status
- [ ] Implement ablation checks in `apps/orchestrator/teacher.py`
- [ ] Update CLI/runtime tests
- [ ] Communicate completion via Agent Mail once MCP is stable
