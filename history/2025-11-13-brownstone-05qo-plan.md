# Plan – ccopilot-05qo (World model claims should track confidence + contradictions)

## Goal
Add uncertainty tracking to the world-model claim pipeline per the scientific review: store confidence scores + timestamps on claims, surface them through CodeAct tools, and introduce basic contradiction detection.

## Steps
1. Inspect `world_model.storage.WorldModelStore` + adapters to understand current schema (`claims` table, etc.) and plan schema changes (confidence REAL, asserted_at TEXT).
2. Update storage + adapter APIs (`record_claim`, `list_claims`) along with migrations/ingest scripts so new fields persist; add contradiction helper that compares new claim bodies against existing rows for the same subject.
3. Wire CodeAct tool wrappers (`apps/codeact/tools/world_model.py`) to accept optional confidence/timestamp inputs (default to 0.5 / now) and expose results, plus extend CLI/wm-inspect where necessary.
4. Add regression tests covering persistence, default confidence, and contradiction flagging; update docs if needed.

## Progress
- 2025-11-13 05:21Z – Created bead ccopilot-05qo and drafted plan. Investigating `world_model.storage` schema next.
- 2025-11-13 05:33Z – Extended `world_model/schema.sql` + `WorldModelStore` to add `confidence`/`asserted_at` columns (with auto-migration), updated adapters to accept the new fields, and added contradiction detection heuristics.
- 2025-11-13 05:41Z – Wired CodeAct tools + ingest script to pass/default confidence values, updated wm-inspect CLI to display the metadata, and added adapter/tool unit tests (`tests/test_world_model_adapter.py`, `tests/test_codeact_world_model_tools.py`, `tests/test_query_world_model.py`). Targeted suites all passing.
