# Plan – ccopilot-92h (World model query CLI should default to outputs path)

## Goal
`scripts/query_world_model.DEFAULT_STORE` still points to `world_model/state.sqlite`, but the pipeline/ingest now write to `outputs/world_model/state.sqlite`. The CLI and tests drift as a result (tests even assert the old path). Need to align the default path, update tests, and document the change so contributors don't hit missing file errors.

## Steps
1. Update `DEFAULT_STORE` and any related CLI messaging/help text to reference `outputs/world_model/state.sqlite`.
2. Adjust `tests/test_query_world_model.py` to match the new default and ensure the ingest helper still writes to the same location used by docs/scripts.
3. Run the query suite (pytest tests/test_query_world_model.py -q).
4. Update plan + bead, notify via Agent Mail.

## Progress
- 2025-11-12 11:22Z – GreenBear opened ccopilot-92h, reserved query CLI/test files, and began updating the default world-model path.
- 2025-11-12 11:23Z – Updated `DEFAULT_STORE` + tests to point at `outputs/world_model/state.sqlite`; `pytest tests/test_query_world_model.py -q` → 11 passed.
