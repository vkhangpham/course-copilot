# Plan – ccopilot-xbpv (Portal should resolve external manifest paths relative to repo root)

## Goal
When manifest entries point outside `outputs/`, `_relative_manifest_path` currently interprets them relative to the portal process CWD, which may diverge from the repo. Resolve them relative to `settings.repo_root` so paths like `config/scientific_config.yaml` remain stable.

## Steps
1. Update `_relative_manifest_path` to detect relative/absolute paths outside outputs and resolve them against `settings.repo_root` before calling `_relative_to_outputs`.
2. Add targeted tests exercising a repo-root path and run `pytest tests/test_portal_backend.py -q`.
3. Communicate completion + close bead.

## Progress
- 2025-11-13 00:38Z – Plan drafted.
- 2025-11-13 00:41Z – `_relative_manifest_path` now resolves via repo root; `pytest tests/test_portal_backend.py -q` passes.
