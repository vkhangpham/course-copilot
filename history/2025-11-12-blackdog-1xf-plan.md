# Plan – ccopilot-1xf (Hide notebook preflight entries)

Goal: prevent the portal API/UI from rendering NotebookPublisher’s `kind="preflight"` records as if they were real notebook sections.

Steps:
1. ☑ Update portal backend `_parse_notebook_exports` to skip entries whose `kind` is `preflight`.
2. ☑ Adjust the mocked manifest in `tests/test_portal_backend.py::_write_run` to include a preflight entry so we have coverage.
3. ☑ Extend the existing portal tests to assert that only real sections show up in `RunDetail`/`/notebook-exports` responses when a preflight entry is present.
4. ☑ Filter manifest-derived exports in `frontend/components/run-detail-section.tsx` so the UI also ignores preflight entries when it falls back to the raw manifest array.
