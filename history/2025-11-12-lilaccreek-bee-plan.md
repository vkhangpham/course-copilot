# ccopilot-bee plan – Resolve config-relative paths (LilacCreek · 2025-11-12)

## Why
`config/pipeline.yaml` stores paths like `world_model/schema.sql` relative to the repo root. When the CLI runs from another directory (common in CI) and only passes `--repo-root`, the config loader still resolves those strings against the current working directory, so dataset/rubric paths point at `/tmp/.../config/data/...` and bootstrap fails before running.

## Tasks
1. Teach `load_pipeline_config` to absolutize `world_model.*` and `evaluation.*` path fields relative to the repo root (or the config directory by default). *(Done @ 01:18 UTC)*
2. Pass `repo_root` into `load_pipeline_config` from `bootstrap_pipeline` so the canonical CLI can rebase relative paths even when executed elsewhere. *(Done @ 01:18 UTC)*
3. Add a regression test (`test_cli_handles_relative_paths_inside_config`) that rewrites the temp YAML to relative strings, runs the CLI from a foreign CWD with only `--repo-root`, and asserts the run succeeds. *(Done @ 01:19 UTC)*
4. Run targeted suites: `pytest tests/test_cli_run_poc.py -q` and `pytest tests/test_core_modules.py -q`. *(Done @ 01:20 UTC)*

## Notes
- Helper `_absolutize_pipeline_paths` currently covers `world_model` and `evaluation`. Extend it if future sections introduce additional path fields.
