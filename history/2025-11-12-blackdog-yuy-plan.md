# Plan – ccopilot-yuy (2025-11-12)

Objective: audit the recent orchestrator/portal/notebook changes for latent bugs or regressions, capture findings, and patch high-impact issues.

## Steps
1. ☑ Recon: scanned TeacherOrchestrator, pipeline runtime, notebook tooling, and portal surfaces; noted ablation + client edge cases still at risk.
2. ☑ Static checks: focused on ablation gating (world model + recursion) and notebook export preflight fallbacks; confirmed manifests/portal assumptions. Adjusted orchestrator so we skip the SQLite world-model pull entirely when ablated, while still feeding dataset highlights to plan/lecture generation and leaving manifests blank.
3. ☑ Fixes: patched prior ablation + notebook guard issues and, as part of the ongoing audit, fixed the portal run-detail slug so overrides display correctly (`apps/portal_backend/main.py`, `tests/test_portal_backend.py`).
4. ☐ Continue audit passes (pipeline warnings, portal endpoints, CLI surfaces) and wrap up with findings + any follow-up bead recommendations. *(In progress — recently patched portal slug + export path regressions; next focus: student loop + CLI surfaces.)*

### 2025-11-12 01:20 UTC update (LilacCreek)
- Found an additional regression path: pipeline YAML paths were still resolved relative to the caller’s cwd when the CLI ran from outside the repo. Fixed via ccopilot-bee (rebased `load_pipeline_config` paths, added regression tests, docs). This closes one of the audit items from Step 2 and keeps CI invocations stable.

### 2025-11-12 01:22 UTC update (LilacCreek)
- With the config fix merged, resuming the audit’s ablation/portal review (steps above). Next log entry will capture any new findings or confirm we’re green.

### 2025-11-12 01:27 UTC update (LilacCreek)
- Found that the teacher orchestrator still emitted `world_model_highlights` artifacts even when the `no_world_model` ablation was active, which undermines the toggle (portal + manifest showed highlights despite the subsystem being “disabled”). Added a guard so highlight JSON is only written when the world model is enabled, and extended the CLI test to assert the manifest omits the path when the ablation is on.

### 2025-11-12 02:06 UTC update (PurpleBear)
- While auditing the portal endpoints, noticed notebook exports dropped both the notebook slug override and the source `path`. Fixed ccopilot-yuy sub-issues ccopilot-axl/84h/ho3 so run details now show the correct slug and per-export path (with proper sandboxing). Tests updated (`tests/test_portal_backend.py`). Continuing audit with an eye on student loop + CLI summaries.
- Also refreshed `tests/test_cli_run_poc.py::test_cli_no_world_model_uses_dataset_highlights` to assert the new `[highlights] (dataset)` label now that the CLI distinguishes between world-model vs dataset fallbacks.
