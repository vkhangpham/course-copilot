# Plan – ccopilot-0un8 (Add wm-inspect summary command)

## Goal
Ops folks asked for a quick way to confirm whether the world-model snapshot was ingested correctly without dumping entire tables. `wm-inspect` only exposes verbose listings, so this bead adds a `summary` command that prints row counts (concepts/authors/papers/timeline/claims/definitions/artifacts) with JSON output for automation.

## Steps
1. Finish this plan + notify other agents about the new bead/reservations.
2. Add summary helpers in `scripts/query_world_model.py` that query row counts and normalize artifact metadata.
3. Add a Typer command (`wm-inspect summary`) that prints a rich table by default and supports `--json` like the other commands.
4. Extend `tests/test_query_world_model.py` with regression coverage for the new helper/command and run `pytest -q`.
5. Send status via Agent Mail, update bd with results, and close the bead once merged.

## Progress
- 2025-11-12 23:07Z – Opened ccopilot-0un8, reserved wm-inspect/query tests, and drafted the plan.
- 2025-11-12 23:12Z – Realized summary command already existed; pivoting scope to enhance artifact metadata (quiz counts, outline weeks) instead.
- 2025-11-12 23:20Z – Added artifact metadata summarizer + CLI table output + JSON fields; updated wm-inspect tests.
- 2025-11-12 23:21Z – `pytest tests/test_query_world_model.py tests/test_wm_inspect_cli.py -q` → 25 passed.
