# Plan – ccopilot-29o8 (Portal should never leak absolute artifact paths)

## Goal
Sanitize portal responses so manifest fields pointing outside `outputs/` or the repo root never expose absolute filesystem paths.

## Steps
1. Reproduce the leak by writing a manifest with `science_config_path` set to an absolute `/tmp/...` value and confirming `/runs/{id}` returns that absolute path.
2. Update `_relative_to_outputs` (and related helpers if needed) to clamp the fallback to a basename-only string when a path cannot be relativized to outputs/ or repo root.
3. Extend `tests/test_portal_backend.py` with a regression that asserts sanitized responses only include relative/basename representations for such paths.
4. Run `pytest tests/test_portal_backend.py -q`.

## Progress
- 2025-11-13 04:14Z – Plan drafted; starting reproduction.
- 2025-11-13 04:16Z – Clamped `_relative_to_outputs` fallback to return only the basename when a path can’t be relativized to outputs/ or repo root, and added regression `test_portal_strips_absolute_paths_that_escape_repo` (plus `pytest tests/test_portal_backend.py -q`).
