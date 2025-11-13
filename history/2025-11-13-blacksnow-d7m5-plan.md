# Plan – ccopilot-d7m5 (Portal should preserve repo-relative paths outside outputs)

## Goal
Ensure portal sanitization preserves enough information for paths (like `science_config_path`) that live outside `outputs/`; currently they’re reduced to just the filename.

## Steps
1. Adjust `_relative_to_outputs` in `apps/portal_backend/main.py` to fall back to repo-root-relative (and finally absolute) paths instead of truncating to `name`.
2. Update tests (and any frontend expectations) to cover paths outside outputs.
3. Communicate completion + close bead.

## Progress
- 2025-11-13 00:15Z – Reserved files, scoped plan, change in progress.
