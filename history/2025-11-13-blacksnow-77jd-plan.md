# Plan – ccopilot-77jd (Add CLI flag for scientific config override)

## Goal
Allow operators to point the CourseGen CLI at a custom scientific evaluation config without editing files or exporting env vars by adding a `--science-config` flag to both the shim (`apps/orchestrator/run_poc.py`) and the canonical CLI (`ccopilot/cli/run_poc.py`).

## Steps
1. Update `apps/orchestrator/run_poc.py` parser + forwarding logic to accept `--science-config` and pass it along when provided (resolving relatives against `--repo-root`).
2. Extend `ccopilot/cli/run_poc.py` parser to accept `--science-config`, resolve paths, and supply `science_config_path` to `bootstrap_pipeline`.
3. Add regression tests (`tests/test_apps_run_poc.py`, `tests/test_cli_run_poc.py`) covering flag forwarding + runtime behavior, then run focused pytest.
4. Document the new flag in README/WORLD_MODEL_TOOLING, send status via Agent Mail, and close the bead once reviewed.

## Progress
- 2025-11-12 23:30Z – Reserved files, announced intent via Agent Mail, drafted plan.
- 2025-11-12 23:37Z – Added `--science-config` flag to shim + canonical CLI, updated docs, and extended forwarding/tests; `pytest tests/test_apps_run_poc.py tests/test_cli_run_poc.py -q` → 30 passed.
