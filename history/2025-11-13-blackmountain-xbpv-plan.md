# Plan – ccopilot-xbpv (Portal should resolve external manifest paths relative to repo root)

## Snapshot – 2025-11-13 02:45 UTC
- Owner: BlackMountain (codex-cli)
- Scope: ensure `_relative_manifest_path` handles manifest entries that point outside `outputs/` even when the portal runs from a different CWD.
- Constraints: respect bd/beads workflow, coordinate via Agent Mail, add regression tests in `tests/test_portal_backend.py`.

## Step-by-step progress
1. **Reproduce** – Inspected `apps/portal_backend/main.py` + existing portal tests to confirm `_relative_manifest_path` only trusts `settings.resolve_path`, which rejects paths outside `outputs/`. Added failing scenario locally (relative `../config/...` entries) to observe absolute paths leaking when CWD changes. ✅
2. **Implement fix** – Updated `_relative_manifest_path` fallback to resolve relative entries against `settings.outputs_dir` before re-running `_relative_to_outputs`, ensuring results stay repo-root-relative even outside `outputs/`. ✅
3. **Regression tests** – Added `test_relative_manifest_paths_use_repo_root_for_external_files` covering repo-root assets + cwd hops; re-ran `pytest tests/test_portal_backend.py` (20/20 passing). ✅

## Next actions
- [ ] Prepare commit referencing `ccopilot-xbpv` once review complete.
- [ ] Close bead + release file reservations after final verification.
