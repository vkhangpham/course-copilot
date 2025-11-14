# Plan – ccopilot-c4wn (Portal health endpoint should not enumerate all runs)

## Goal
Make `/health` lightweight by avoiding a full manifest scan; it should just inspect the latest run id and return immediately even when hundreds of runs exist.

## Steps
1. Confirm current behaviour (`health()` calls `_list_runs(settings)` with no limit) and measure the surface area touched.
2. Update `health()` to fetch only the first manifest (e.g., `_iter_manifest_paths` head or `_list_runs(..., limit=1)`), returning the run id without parsing the rest.
3. Adjust/extend portal backend tests to cover the new logic (ensure health call doesn’t require multiple runs and still reports latest id when present).
4. Run targeted pytest (`tests/test_portal_backend.py`).

## Status
- 2025-11-13 04:57Z – Plan drafted; beginning audit of current `/health` implementation.
