# Notebook pre-flight helper plan (ccopilot-ofe)

## Remaining tasks once shared files free

1. **CLI wrapper** – add `--skip-notebook-create` to `apps/orchestrator/run_poc.py` so the top-level entry point forwards the flag to `ccopilot.cli.run_poc`. Keep help text concise so the minimal CLI story still holds.
2. **Notebook mock/tests** – extend `tests/mocks/notebook_api.py` so the patched client exposes `ensure_notebook()` and the FastAPI app accepts `POST /api/notebooks`. Update `tests/test_open_notebook_tools.py` to either (a) set `OPEN_NOTEBOOK_AUTO_CREATE=0` for the existing tests or (b) assert that the pre-flight call hits the mock. Also reset `_ENSURED_NOTEBOOKS` between tests to avoid cross-test leakage.
3. **README/doc** – add a short note under the Open Notebook section explaining the auto-create helper, the new env flag (`OPEN_NOTEBOOK_AUTO_CREATE`), and the `--skip-notebook-create` override.
4. **Manifest hint coverage** – once BlueCastle’s notebook export changes land, re-run `pytest tests/test_cli_run_poc.py` (after patching the mock) to ensure the CLI still prints the `[notebook]` hints with the new metadata.

## Coordination notes

- BlueCastle is working in the same files for ccopilot-5fr; wait for their confirmation before re-reserving the orchestrator/README/test surfaces.
- BlackHill is updating the notebook mock for ccopilot-odw; once their patch lands, sync to avoid double-editing the ASGI transport bits.

## Validation queue

When the files open up:

- `pytest tests/test_open_notebook_client.py tests/test_open_notebook_preflight.py`
- `pytest tests/test_open_notebook_tools.py`
- `pytest tests/test_cli_run_poc.py`
- `pytest tests/test_pipeline_runtime.py -k notebook` (quick targeted pass)

## 2025-11-12 @ LilacStone note
- Hardened the auto-create cache so it keys on `(api_base, slug)`—otherwise a successful preflight against localhost would skip notebook creation for a later run against staging with the same slug. Added regression coverage in `tests/test_open_notebook_tools.py::test_auto_create_cache_scoped_per_api_base` and refreshed the suite.
