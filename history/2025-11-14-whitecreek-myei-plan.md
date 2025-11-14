# Plan – ccopilot-myei (PoC orchestrator CLI)

## Goal
Implement the minimal `apps/orchestrator/run_poc.py` shim so it matches `docs/PLAN.md` & `docs/PoC.md`: only expose constraints path, handcrafted dataset, notebook slug, and ablation toggles while always resolving relative flags against `--repo-root`.

## Steps
1. Verify the parser accepts both `--concept` and `--concepts` so documentation commands remain valid.
2. Make the CLI honor `COURSEGEN_DATASET_DIR` before falling back to the repo defaults, while leaving `--concepts` higher priority.
3. Confirm the forwarded arguments land on `ccopilot.cli.run_poc` with resolved absolute paths.
4. Document the behavior (history + agent mail) and record test coverage; run `pytest tests/test_apps_orchestrator_run_poc.py -q`.

## Progress
- 2025-11-14 WhiteCreek: Added the `--concept` alias plus parser tests to keep the minimal CLI stable with the docs, then updated the shim to prefer `COURSEGEN_DATASET_DIR` when present and expanded tests to cover env-vs-flag precedence. Tests still pass (`pytest tests/test_apps_orchestrator_run_poc.py -q`), bead `ccopilot-myei` is claimed, and the team has been notified via MCP Agent Mail.

## Next
- Consider adding a short note to `docs/PoC.md` (or another handbook) so operators know about the env override. If no doc update is welcomed, this plan is effectively done—switch to the next bead or audit area needing attention.
