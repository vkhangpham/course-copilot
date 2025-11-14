# Plan – ccopilot-msmp (CLI highlight hint should name world_model source)

## Goal
Ensure the CourseGen CLI clearly labels highlight provenance for both world-model and dataset runs so ablation diagnostics are visible directly in stdout.

## Steps
1. Reproduce the existing behavior and capture why `[highlights]` messages omit the `(world_model)` suffix while dataset fallbacks already show `(dataset)`.
2. Patch `_print_highlight_hint` in `ccopilot/cli/run_poc.py` so any non-empty `highlight_source` is appended to the label, and update the CLI tests to expect `(world_model)`.
3. Run the targeted CLI test subset and announce the fix via Agent Mail + bead notes.

## Progress
- 2025-11-13 04:46Z – Investigated CLI output: world-model runs only print `[highlights] saved to …`, making it impossible to distinguish default runs from other sources. Dataset runs already include `(dataset)`.
- 2025-11-13 04:49Z – Updated `_print_highlight_hint` to always include the recorded source (world_model, dataset, or other) and tightened `tests/test_cli_run_poc.py` to assert the `(world_model)` suffix.
