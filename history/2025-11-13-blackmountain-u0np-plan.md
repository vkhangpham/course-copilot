# Plan – ccopilot-u0np (run_poc shim should auto-detect scientific config)

## Snapshot – 2025-11-13 03:05 UTC
- Owner: BlackMountain
- Scope: ensure `apps/orchestrator/run_poc` forwards `--science-config` whenever `<repo>/config/scientific_config.yaml` exists, matching the CLI help + portal expectations.

## Progress log
1. **Investigate gap** – Confirmed the shim only passed `--science-config` when explicitly provided, so default runs never tagged `science_config_path` in manifests. ✅
2. **Implement auto-detect** – Added `DEFAULT_SCIENCE_CONFIG_REL` and logic to inject the default path when the file exists (while still respecting explicit overrides). ✅
3. **Regression tests** – Expanded `tests/test_apps_run_poc.py` to assert default forwarding in the real repo, cover repo-root overrides with/without the file, and re-ran `pytest tests/test_apps_run_poc.py` (9/9). ✅

## Next
- [ ] Commit referencing `ccopilot-u0np` once reviews land.
- [ ] Close bead + notify thread after verification.
