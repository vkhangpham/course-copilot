# Plan – ccopilot-0hfh (CLI should mention highlight source even when no artifact)

## Goal
Ensure the CLI still surfaces highlight provenance when orchestrator runs skip writing a highlight artifact (e.g., dataset fallback with empty slices).

## Steps
1. Reproduce the silent-path behavior by calling `_print_highlight_hint` with `highlights=None` but `highlight_source` populated.
2. Update `_print_highlight_hint` to emit a message whenever `highlight_source` exists, even if no artifact was generated, and add CLI regression coverage.
3. Run the targeted CLI tests and notify via Agent Mail.

## Progress
- 2025-11-13 05:16Z – Confirmed the CLI prints nothing when `artifacts.highlights` is `None` even if `highlight_source` is defined; dataset-only runs with empty highlight slices have no provenance hint.
- 2025-11-13 05:19Z – Updated `_print_highlight_hint` to fall back to `[highlights] (<source>) not generated (no highlight artifact)` when the file is missing. Added `tests/test_cli_run_poc.py::test_cli_highlight_hint_mentions_source_without_artifact` and ran `pytest tests/test_cli_run_poc.py -k highlight -q`.
