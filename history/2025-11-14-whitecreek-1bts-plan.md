# Plan – ccopilot-1bts (TA role tests for split_fields)

## Goal
Ensure the TA role tests reflect the shared `split_fields` utility so we guard semicolon/comma delimiters consistently across explainer timeline parsing.

## Steps
1. Review existing TA role tests (especially `tests/test_explainer.py` and `tests/test_timeline_synthesizer.py`) to understand how they currently exercise timeline parsing.
2. Add regression coverage that proves `Explainer` consumes comma-delimited `related_concepts` and that `TimelineSynthesizer` both splits comma-separated lists and returns matching concepts after filtering.
3. Run the focused pytest suites (`tests/test_explainer.py` and `tests/test_timeline_synthesizer.py`), summarize results in this history log, and close the bead once the tests pass (including a commit if needed).

## Progress
- 2025-11-14 WhiteCreek: Added tests ensuring both `Explainer` and `TimelineSynthesizer` handle comma-delimited `related_concepts` via `split_fields`, and verified `pytest tests/test_explainer.py tests/test_timeline_synthesizer.py -q` passes.

## Next
- Confirm the new tests pass (`pytest tests/test_explainer.py tests/test_timeline_synthesizer.py`) and then mark the bead complete + send a wrap-up agent mail referencing the added coverage.
