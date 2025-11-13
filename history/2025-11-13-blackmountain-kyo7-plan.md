# Plan – ccopilot-kyo7 (Domain table should expose taxonomy summaries)

## Snapshot – 2025-11-13 04:05 UTC
- Owner: BlackMountain
- Problem: `apps/codeact/tools/data._load_domain_rows` still populated the deprecated `focus` column from taxonomy entries, so `run_sql_query` returned NULL even though `taxonomy.yaml` stores domain `summary` strings. Need to surface the current field (with backward-compatible fallback).

## Progress
1. **Reproduce** – Ran `run_sql_query("SELECT id, title, focus FROM domains ...")` and confirmed the focus column was always NULL despite summaries living in `taxonomy.yaml`. ✅
2. **Fix** – Updated `_load_domain_rows` to emit both `summary` and (legacy) `focus` values (defaulting to whichever exists) and expanded `_register_domains_table` to include both columns so existing queries keep working. ✅
3. **Tests** – Added `test_run_sql_query_exposes_domain_summaries` to `tests/test_codeact_data.py` and executed `pytest tests/test_codeact_data.py` (23/23). ✅

## Next
- [ ] Commit referencing `ccopilot-kyo7` and close bead.
