# Plan – ccopilot-gv3b (Allow timeline tool to record concept-less events)

## Snapshot – 2025-11-13 05:25 UTC
- Owner: BlackMountain
- Issue: `WorldModelAdapter.append_timeline_event` and the CodeAct wrapper required `related_concept`, so agents could not log timeline milestones without a concept even though the schema/ingest layer now supports NULL `related_concept` entries.

## Progress
1. **Reproduce** – Called `append_timeline_event(..., related_concept=None)` after ingesting the handcrafted dataset and confirmed it raised `ValueError("At least one concept id is required")`. ✅
2. **Implement** – Made `related_concept` optional in both the adapter and the CodeAct wrapper, only validating concepts when provided and inserting NULL otherwise. ✅
3. **Regression tests** – Added `test_append_timeline_event_allows_missing_concept` in `tests/test_codeact_world_model_tools.py`; ran `pytest tests/test_codeact_world_model_tools.py` (15/15). ✅

## Next
- [ ] Commit referencing `ccopilot-gv3b` and close the bead.
