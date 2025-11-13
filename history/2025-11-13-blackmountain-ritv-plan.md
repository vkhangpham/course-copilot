# Plan – ccopilot-ritv (Ingest should keep timeline events without concept links)

## Snapshot – 2025-11-13 03:58 UTC
- Owner: BlackMountain
- Issue: `_insert_timeline` only emitted rows when `concept_ids` was non-empty, so timeline milestones without `related_concepts` vanished even though `observations.related_concept` is nullable.

## Progress
1. **Reproduce** – Generated a minimal dataset via `_write_minimal_dataset`, blanked the `related_concepts` column, and confirmed no observation rows were inserted. ✅
2. **Fix** – Updated `_insert_timeline` to append a single `(…, None, citation)` row when `concept_ids` is empty while keeping existing validation for explicit concept IDs. ✅
3. **Tests** – Added `test_ingest_keeps_events_without_related_concepts` in `tests/test_ingest_handcrafted.py` and ran `pytest tests/test_ingest_handcrafted.py` (9/9). ✅

## Next
- [ ] Commit referencing `ccopilot-ritv` and close the bead once reviewed.
