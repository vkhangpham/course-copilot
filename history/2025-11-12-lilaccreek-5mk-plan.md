# ccopilot-5mk plan – Anchor ccopilot/cli/run_poc paths (LilacCreek · 2025-11-12)

## Why
`ccopilot/cli/run_poc.py` accepts `--repo-root`, but it still resolves `--config`, `--constraints`, `--output-dir`, and dataset overrides relative to the caller's CWD. When you run `python -m ccopilot.cli.run_poc --repo-root /abs/repo` from outside the repo (or invoke the console script), the defaults (`config/pipeline.yaml`, etc.) point to the wrong directory and the CLI crashes before bootstrap. Our `apps/orchestrator/run_poc` shim papers over this by pre-resolving paths, but the canonical CLI remains broken for direct users and automated tooling.

## Tasks
1. Mirror the `_resolve_path(..., base=repo_root)` logic inside `ccopilot/cli/run_poc.main` so every path argument respects the repo root when provided. *(Done @ 01:03 UTC)*
2. Extend the CLI test suite (likely `tests/test_cli_run_poc.py`) with a subprocess-style test that invokes the cli module from a temp directory using `--repo-root` to ensure defaults resolve correctly. *(Done @ 01:04 UTC – see `test_cli_resolves_relative_paths_against_repo_root`)*
3. Update docs/README snippets mentioning the CLI to clarify that relative overrides are anchored to `--repo-root` across both entry points. *(Done @ 01:05 UTC – README + AGENTS updated)*
4. Run the affected pytest modules and capture the command log for the bead. *(Done @ 01:06 UTC – `pytest tests/test_cli_run_poc.py -q` and `pytest tests/test_apps_run_poc.py -q`)*

## Notes
- Keep `_resolve_path` helper DRY by importing from a shared utility if practical, or re-implement locally with identical semantics.
- No behavior change for callers already passing absolute paths; only relative inputs should be affected.
