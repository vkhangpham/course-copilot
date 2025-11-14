# Plan – ccopilot-u1d8 (Normalize related_concept splitting)

## Goal
Multiple components parse multi-valued `related_concepts` fields (ingest loader, timeline synthesizer, explainer) using slightly different heuristics. This causes subtle divergence when new delimiters are introduced, and there is no shared test coverage. Introduce a single utility that splits CSV/semicolon lists and share it across the stack so the behavior stays consistent.

## Steps
1. Create `ccopilot/utils/split_fields.py` with `split_fields()` that handles strings or iterables and splits on commas/semicolons.
2. Replace the `_split`/_`_split_list` helpers in `scripts/handcrafted_loader.py` and `scripts/ingest_handcrafted.py` with the new helper, keeping validation semantics intact.
3. Update `apps/orchestrator/ta_roles/explainer.py` and `timeline_synthesizer.py` to rely on the new helper for parsing `related_concepts`.
4. Add regression coverage via `tests/test_split_fields.py` plus rerun relevant modules' tests.
5. Document progress/history and close the bead once CI/tests pass.

## Progress
- 2025-11-14 05:20 UTC – Utility implemented, loader/ingest/TA roles refactored, tests added, and `pytest` focused suites green.
