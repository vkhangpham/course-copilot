# Plan – ccopilot-8my (Timeline rows without id vanish during dataset load)

## Goal
`load_dataset()` relies on `_load_csv`, which currently drops any CSV row lacking an `id` column. The handcrafted timeline uses `year,event,...` columns, so every timeline entry is silently discarded. Need to preserve non-empty rows regardless of `id` presence and keep authors/papers validation intact.

## Steps
1. Add regression tests in `tests/test_handcrafted_loader.py` proving `load_dataset(...).timeline` contains events and that missing IDs in authors/papers are still surfaced via `_unique_ids`.
2. Update `_load_csv` to keep non-empty rows while still ignoring blank lines and supporting caller-specific `require_id` semantics if needed.
3. Run the handcrafted loader test slice.
4. Update plan + bead state, communicate via Agent Mail.

## Progress
- 2025-11-12 10:57Z – GreenBear opened ccopilot-8my, reserved loader/test files, and began fixing the timeline ingestion bug.
- 2025-11-12 10:59Z – Patched `_load_csv` to retain any non-empty row (timeline events now load) and extended `tests/test_handcrafted_loader.py` smoke test; `pytest tests/test_handcrafted_loader.py -q` ⇒ 5 passed.
