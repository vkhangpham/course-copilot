# Plan – ccopilot-0dn (Add tests for wm-inspect CLI)

## Goal
`scripts/query_world_model.py` powers the `wm-inspect` Typer CLI, but we currently only test the underlying module functions. Add CLI-level regression coverage using Typer’s `CliRunner` so we ensure the entry point succeeds on happy paths and handles missing stores cleanly.

## Steps
1. Create `tests/test_wm_inspect_cli.py` that ingests a temp store, then runs commands like `concepts` and `timeline` via `CliRunner` (asserting exit code 0 and JSON output contains expected data).
2. Add a negative test (missing store path) to confirm we surface the expected error message/exit code.
3. Run `pytest tests/test_wm_inspect_cli.py -q`.
4. Update plan + notify via Agent Mail.

## Progress
- 2025-11-13 02:45Z – Added `tests/test_wm_inspect_cli.py` covering happy-path and missing-store flows (plus repo-root override). `pytest tests/test_wm_inspect_cli.py -q` → 3 passed.
