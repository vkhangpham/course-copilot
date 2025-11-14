# 2025-11-12 BlueCastle — ccopilot-u7y portal hardening

## Context
- Bead **ccopilot-u7y**: "Harden portal file path resolution".
- Goal: ensure portal backend (`apps/portal_backend/main.py`) never serves arbitrary paths from manifests; restrict to `<repo>/outputs/**` and return HTTP 400 on violations.

## Actions
1. Updated `PortalSettings.resolve_path` to resolve all manifest paths relative to `outputs_dir`, reject anything outside via `HTTPException(400)`.
2. Added `_safe_resolve` helper so `/runs` listing gracefully tolerates bad paths while detail endpoints still raise.
3. Extended trace collection + `resolve_path` callers to use the safe helper where we don’t want to fail the entire listing.
4. Adjusted FastAPI tests (`tests/test_portal_backend.py`) to expect HTTP 400 and verify the new guard.
5. Re-ran `pytest tests/test_portal_backend.py` (passes).

## Next steps
- None for ccopilot-u7y; portal endpoints now hard-fail on escape attempts while listings remain resilient.
