# Plan – ccopilot-wf7 (Extend wm-inspect tests to papers and authors)

## Goal
Continue the CLI regression coverage by adding Typer-based tests for `wm-inspect papers` and `wm-inspect authors`, ensuring keyword filters work and env overrides remain wired.

## Steps
1. Reuse the temp store helper from `tests/test_wm_inspect_cli.py`.
2. Add tests invoking `papers --keyword relational --json` and `authors --keyword stonebraker --json`, asserting expected rows.
3. Run `pytest tests/test_wm_inspect_cli.py -q` and document results + Agent Mail note.

## Progress
- 2025-11-13 03:05Z – Plan drafted; will add papers/authors coverage next.
- 2025-11-13 03:07Z – Added papers/authors CLI tests and ran `pytest tests/test_wm_inspect_cli.py -q` (7 passed).
