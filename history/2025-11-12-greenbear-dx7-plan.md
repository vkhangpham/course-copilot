# Plan – ccopilot-dx7 (Timeline ingestion should accept event_label column)

## Goal
`observations.event_label` is NOT NULL, but `scripts/ingest_handcrafted` only reads the `event` column from timeline CSVs. Earlier tests + docs still mention `event_label`, so rows using that header end up inserting NULL labels (or failing validation). Normalize both column names during ingest and propagate the normalized value to DB + snapshots.

## Steps
1. Extend `tests/test_ingest_handcrafted.py` with a dataset that uses `event_label` and verify the ingested observations keep that text.
2. Update `_load_datasets` and `_insert_timeline` to coalesce `event`/`event_label`, ensuring validation errors reference whichever value exists.
3. Run `pytest tests/test_ingest_handcrafted.py -q`.
4. Update plan log, send Agent Mail, and close the bead when merged.

## Progress
- 2025-11-12 11:27Z – GreenBear opened ccopilot-dx7, reserved ingest/test files, and is adding setext-style event label normalization for timeline rows.
- 2025-11-12 11:30Z – Added minimal dataset regression for `event_label` timelines, normalized ingest `_load_datasets`/`_insert_timeline`, and ran `pytest tests/test_ingest_handcrafted.py -q` → 5 passed.
