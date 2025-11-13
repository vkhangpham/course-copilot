# Plan – ccopilot-o3u6 (Record scientific config path in manifests and CLI output)

## Goal
Runs should specify which scientific evaluator config was used. Currently the path only appears in provenance logs (if at all) and isn’t surfaced in the manifest or CLI summaries. Add first-class metadata so reviewers can trace each run back to the exact config file.

## Steps
1. Extend `PipelineContext`/`bootstrap_pipeline` to store the resolved science config path (if any) alongside the loaded config dict, logging it in provenance.
2. Update `apps/orchestrator/pipeline.py` to embed `science_config_path` in the run manifest + any relevant artifacts.
3. Surface the path in CLI summaries (e.g., `[artifacts] science_config=/abs/path/...`) and add regression coverage (`tests/test_cli_run_poc.py`, `tests/test_pipeline_runtime.py`).
4. Document the new metadata in README/WORLD_MODEL_TOOLING, notify via Agent Mail, and close the bead.

## Progress
- 2025-11-12 23:40Z – Reserved files, announced plan, drafted outline.
- 2025-11-12 23:48Z – Added science_config_path tracking (context/bootstrap), embedded it in manifest + CLI `[artifacts]`, updated docs, and expanded tests (`pytest tests/test_cli_run_poc.py tests/test_pipeline_runtime.py -q` → 36 passed).
