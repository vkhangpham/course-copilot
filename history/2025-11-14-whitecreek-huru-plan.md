# Plan – ccopilot-huru (Document dataset override env var)

## Goal
Update the runbook so operators know about the `COURSEGEN_DATASET_DIR` env var and the `--concept` alias when running the PoC CLI, keeping the docs aligned with the recent CLI behavior.

## Steps
1. Confirm where the minimal `apps/orchestrator/run_poc.py` usage is described (e.g., `docs/PoC.md` Step 3) so we can place the note there.
2. Add a short paragraph describing the `COURSEGEN_DATASET_DIR` override and mention that `--concept` is an alias for `--concepts` so the documented command continues to work.
3. Include a note about exporting the env var when running from a different working directory so the dataset resolution matches CLI defaults.
4. Record the change in this history file, cite the updated doc sections, and close the bead once the docs commit is ready.

## Progress
- 2025-11-14 WhiteCreek: Added guidance to `docs/PoC.md` step 3 describing how to set `COURSEGEN_DATASET_DIR` for dataset overrides and reminding operators that `--concept` aliases `--concepts`. No tests required.

## Next
- Modify `docs/PoC.md` accordingly and note the change in this history entry before closing the bead.
