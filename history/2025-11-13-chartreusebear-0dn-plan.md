# Plan – ccopilot-0dn (Add tests for wm-inspect CLI)

## Goal
`wm-inspect` has no automated coverage, so env regressions (COURSEGEN_REPO_ROOT, missing stores, etc.) only surface via manual testing. Add lightweight tests that invoke the Typer app against a temp store to ensure the CLI resolves default paths correctly and renders JSON output when requested.

## Steps
1. Build a minimal world-model store via `ingest_handcrafted` into a temp dir.
2. Add tests under `tests/test_wm_inspect_cli.py` that:
   - run `scripts.query_world_model.concepts` via Typer’s Testing runner with `--json` and assert results
   - ensure `COURSEGEN_REPO_ROOT` overrides are honored and missing stores raise `BadParameter`.
3. Run `pytest tests/test_wm_inspect_cli.py -q` (and ideally the targeted suite) and document results + Agent Mail note.

## Progress
- 2025-11-13 02:42Z – Plan drafted; starting on store setup.
- 2025-11-13 02:45Z – Added `tests/test_wm_inspect_cli.py` with Typer runner coverage (JSON output, missing store errors, repo-root env); `pytest tests/test_wm_inspect_cli.py -q` passes (3 tests).
