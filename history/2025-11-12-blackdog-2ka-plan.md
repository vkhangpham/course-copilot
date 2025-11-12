# Plan – ccopilot-2ka (Portal should return relative notebook export paths)

Problem: after ccopilot-ho3 the portal exposes absolute filesystem paths for notebook exports (e.g., `/private/var/.../course_plan.md`). That leaks host layout, which AGENTS.md discourages. We should emit paths relative to the portal `outputs` root (or provide a download URL).

Steps:
1. ☑ Update `_parse_notebook_exports` so it computes a path relative to `settings.outputs_dir` (e.g., `course_plan.md` or `lectures/module_01.md`). Store that relative string in the response instead of the absolute path.
2. ☑ Extend `tests/test_portal_backend.py` assertions (detail + `/notebook-exports`) to expect relative paths.
3. ☑ Keep `_safe_resolve` for sandboxing, but only return `str(relative_path)`.
4. ☑ Communicate + close bead once merged (status sent via Agent Mail; ready to close).
