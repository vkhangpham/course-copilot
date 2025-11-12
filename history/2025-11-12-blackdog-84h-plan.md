# Plan – ccopilot-84h (Portal notebook export IDs)

1. ☑ Inspect `_parse_notebook_exports` to confirm it only surfaces `note_id`/`section_id`.
2. ☑ Modify the parser to fall back to `response['id']` (and keep existing fields) so the UI gets the canonical identifier even when section_id is absent.
3. ☑ Extend `tests/test_portal_backend.py` helpers/tests to cover the new behavior.
4. ☑ Run the portal test suite to verify (`pytest tests/test_portal_backend.py -q`).
