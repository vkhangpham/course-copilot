# Plan – ccopilot-pqk (World-model CodeAct tools should error when store path missing)

## Goal
`apps/codeact/tools/world_model._adapter` instantiates `WorldModelAdapter` even when the requested SQLite path doesn’t exist. Because `WorldModelStore` auto-creates the file, CodeAct readers silently query an empty database instead of failing fast, leading to missing grounding data. Update the adapter to raise a clear error when the store path is absent and add regression tests covering the failure.

## Steps
1. Reproduce by calling `fetch_concepts(store_path=tmp_path/"missing.sqlite")` and observe it returns an empty list instead of raising.
2. Change `_adapter` to verify `resolved.exists()` before building `WorldModelAdapter`, raising `FileNotFoundError` with the attempted path when missing.
3. Add tests in `tests/test_codeact_world_model_tools.py` asserting `fetch_concepts` raises when the store path is missing and still works for real paths.
4. Run `pytest tests/test_codeact_world_model_tools.py -q`, update this plan, and notify via Agent Mail thread `ccopilot-pqk`.

## Progress
- 2025-11-13 01:44Z – ChartreuseBear filed bead after confirming CodeAct tools silently create empty stores on bad paths.
- 2025-11-13 01:46Z – `_adapter` now checks `Path.exists()` before instantiating `WorldModelAdapter`, added `test_fetch_concepts_missing_store_raises`, and ran `pytest tests/test_codeact_world_model_tools.py -q` (11 passed).
