# Plan – ccopilot-a6d (Extend wm-inspect tests to timeline and claims)

## Goal
`tests/test_wm_inspect_cli.py` currently only covers the `concepts` command. Add Typer-based tests for at least one timeline command (with filters) and a claims command to catch regressions in SQL query plumbing and env overrides.

## Steps
1. Ingest the existing storefront dataset into a temp store (reuse helper) for each test.
2. Add a test that runs `wm-inspect timeline --store ... --concept relational_model --json` and asserts rows include the concept id and year filter.
3. Add a test for `wm-inspect claims` verifying a known concept returns rows with citations; also cover `--json` output.
4. Run `pytest tests/test_wm_inspect_cli.py -q`, update plan + mail thread.

## Progress
- 2025-11-13 03:02Z – Drafted plan; starting timeline test.
- 2025-11-13 03:05Z – Added timeline + claims CLI tests to `tests/test_wm_inspect_cli.py` and ran `pytest tests/test_wm_inspect_cli.py -q` (5 passed).
