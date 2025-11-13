# Plan – ccopilot-4u1 (Add tests for validate-handcrafted CLI)

## Goal
`scripts/validate_handcrafted.py` is our lint entry point but currently lacks regression coverage—no tests assert that `validate-handcrafted` succeeds on clean data or raises when warnings/errors occur. Add pytest-based coverage that spawns the Typer CLI against synthetic datasets so future changes don't silently break the validator flags.

## Steps
1. Add a new test module (`tests/test_validate_handcrafted_cli.py`) that uses Typer's test runner (or subprocess) to run `validate-handcrafted` against:
   - the shipped dataset (expect success, exit code 0).
   - a tampered dataset containing a warning-only condition, confirming `--fail-on-warning` exits non-zero.
2. Use tmp dirs + copies of `data/handcrafted/database_systems` to avoid mutating the canonical dataset.
3. Run `pytest tests/test_validate_handcrafted_cli.py -q`.
4. Update plan + send Agent Mail.

## Progress
- 2025-11-13 01:25Z – Reserved CLI/test files, coordinating with other agents before adding the validate-handcrafted tests.
- 2025-11-13 01:28Z – Added Typer CLI regression tests covering success + `--fail-on-warning` flows; `pytest tests/test_validate_handcrafted_cli.py -q` → 2 passed.
