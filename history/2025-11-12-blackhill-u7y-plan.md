# ccopilot-u7y · Portal path hardening plan

## Context
Portal endpoints currently trust any path recorded in run manifests. A malicious or corrupted manifest could point to files outside the repo/outputs tree, letting the API read arbitrary files on the host.

## Tasks
1. **Add safe path resolution** – update `PortalSettings.resolve_path` to normalize/resolved paths and ensure they live under either `repo_root` or the configured `outputs_dir`. Reject anything outside with an HTTP 400 so operators notice the bad manifest.
2. **Trace helpers** – ensure helpers like `collect_trace_files` and `build_teacher_trace_meta` continue using `resolve_path` so the new guard applies automatically.
3. **Tests** – extend `tests/test_portal_backend.py` with a case where the manifest references a path outside the allowed roots and assert that `/runs/{id}/course-plan` (or similar) returns HTTP 400.
4. **Docs/notes** – mention the constraint in the portal plan if needed (optional once code/docstrings show behavior).

## Status
- [x] Implement safe `resolve_path`
- [x] Add regression test
- [x] Run portal test suite (`pytest tests/test_portal_backend.py`)
- [ ] Communicate status via Agent Mail (pending MCP availability)
