# Plan – ccopilot-y06v (Eval loop should override repo-root env)

## Snapshot – 2025-11-13 03:15 UTC
- Owner: BlackMountain
- Problem: `apps/orchestrator/eval_loop.py` only called `os.environ.setdefault('COURSEGEN_REPO_ROOT', ...)`, so existing env values from other checkouts leaked into evaluator runs even when `--repo-root` was passed. Downstream modules (world-model tools, portal hooks) would reference the wrong repo.

## Progress log
1. **Reproduce** – Confirmed the shim leaves `COURSEGEN_REPO_ROOT` unchanged when already set by running the Typer CLI under a stale env (see new regression test). ✅
2. **Fix** – Updated the CLI to force-overwrite the env var with the resolved repo root, matching the main CourseGen CLI. ✅
3. **Tests** – Added `test_eval_loop_overrides_existing_repo_root_env` to `tests/test_eval_loop_cli.py`; ran `pytest tests/test_eval_loop_cli.py` (3/3 passing). ✅

## Next steps
- [ ] Commit referencing `ccopilot-y06v` once reviews are satisfied.
- [ ] Close bead, release reservations, notify thread.
