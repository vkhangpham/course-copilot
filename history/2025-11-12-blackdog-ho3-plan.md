# Plan – ccopilot-ho3 (Portal should expose notebook export paths)

1. ☑ Inspect portal API + frontend types to confirm `path` is dropped when returning notebook exports.
2. ☑ Update backend (`NotebookExport` model + `_parse_notebook_exports`) to include sanitized `path` values (using `_safe_resolve`), ensuring we don't leak files outside the outputs dir.
3. ☑ Extend `tests/test_portal_backend.py` to assert the path is returned both in `/runs/{id}` detail and `/runs/{id}/notebook-exports` endpoints.
4. ☑ Update frontend `NotebookExportEntry` type + components to consume/display the path, and run portal + UI tests as needed (`pytest tests/test_portal_backend.py -q`).
5. Communicate results + close the bead once merged.
