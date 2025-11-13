# Plan – ccopilot-igw2 (Portal manifest fallback should use repo_root)

## Snapshot – 2025-11-13 03:00 UTC
- Owner: BlackMountain
- Goal: ensure `_relative_manifest_path` interprets fallback paths relative to `settings.repo_root`, not `outputs_dir`, and add regression coverage for repo-root assets expressed as absolute paths.

## Progress Log
1. **Detect regression** – Noted that ccopilot-xbpv patch mistakenly anchored fallback to `settings.outputs_dir`, breaking manifests referencing repo-root configs. ✅
2. **Code fix** – Updated `_relative_manifest_path` fallback to prepend `settings.repo_root` for relative strings while preserving absolute-path handling. ✅
3. **Testing** – Adjusted `test_relative_manifest_paths_use_repo_root_for_external_files` to feed absolute repo-root config/artifact paths and verified normalized output remains `config/...` even when the portal runs from another CWD (`pytest tests/test_portal_backend.py`). ✅

## Next
- [ ] Commit referencing `ccopilot-igw2` once review satisfied.
- [ ] Close bead + release reservations / notify thread.
