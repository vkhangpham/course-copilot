# Plan – ccopilot-j601 (Notebook citations should preserve original casing)

## Snapshot – 2025-11-13 03:50 UTC
- Owner: BlackMountain
- Issue: `_extract_citations` lowercased every token before returning it, so Notebook exports lost proper nouns / canonical citation IDs (e.g., `[Garcia, 2021]` → `garcia, 2021`). Need to dedupe case-insensitively but keep the source text intact.

## Progress
1. **Confirm behavior** – Reproduced the lowercasing by instrumenting `_extract_citations` on mixed-case citations; identified need for case-insensitive dedupe while preserving author/title casing. ✅
2. **Code changes** – Updated `apps/orchestrator/notebook_publisher._extract_citations` to track a lowercase `seen` set but append the original cleaned token, and sorted results using a case-insensitive key so output order remains deterministic. ✅
3. **Tests** – Added `test_extract_citations_preserves_original_casing` under `tests/test_notebook_publisher.py`, covering mixed-case citations plus duplicates; ran `pytest tests/test_notebook_publisher.py` (2/2). ✅

## Next
- [ ] Commit referencing `ccopilot-j601` (done in repo history).
- [ ] Close bead + release reservations once review complete.
