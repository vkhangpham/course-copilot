# Plan – ccopilot-8ry (Timeline ingestion ignores plain 'citation' column)

## Goal
`scripts/ingest_handcrafted._load_datasets` + `_insert_timeline` only look at the `citation_id` column. If a timeline CSV uses `citation` (matching `validate_dataset`), citations silently drop from the world-model observations. Need ingestion to accept both column names, validate them against papers, and persist whichever value is present.

## Steps
1. Extend ingest loader tests (`tests/test_ingest_handcrafted.py`) with a case where the timeline CSV uses `citation` and ensure the row survives with the citation retained.
2. Update `_load_datasets` to normalize `citation_id` from either column and validate accordingly; update `_insert_timeline` to use the normalized field.
3. Run `pytest tests/test_ingest_handcrafted.py -q`.
4. Update plan + bead, send Agent Mail.

## Progress
- 2025-11-12 11:16Z – GreenBear opened ccopilot-8ry, reserved ingest/test files, and started on the timeline citation normalization fix.
- 2025-11-12 11:19Z – Added regression covering `citation` columns plus normalized `_load_datasets`/`_insert_timeline`/snapshot handling; `pytest tests/test_ingest_handcrafted.py -q` → 3 passed.
