# CourseGen PoC (RLM + DSPy CodeAct)

This repository hosts the proof-of-concept for Concepedia’s “CourseGen” pipeline. A Teacher RLM orchestrates TA agents inside a DSPy CodeAct sandbox, grounded by a handcrafted Database Systems world model, and publishes course artifacts to an Open Notebook instance.

## Current Status
- `apps/orchestrator/run_poc.py` runs a stub pipeline that wires the CLI, config loading, and output directory management.
- `docs/ARCHITECTURE.md` captures the concrete module/interface plan derived from `docs/PLAN.md` / `docs/PoC.md`.
- `history/2025-11-11-chartreusestone-plan.md` documents the workstream split and outstanding coordination items.
- Handcrafted Database Systems assets + ingestion pipeline are available under `data/handcrafted/database_systems/` and `scripts/ingest_handcrafted.py`; world-model tools now query the populated snapshot.

## Setup
1. Create/activate a Python 3.11 environment and install the package in editable mode:
   ```bash
   pip install -e .
   ```
2. Populate `config/` as needed (sample YAMLs are provided). _Do **not** commit `.env` values._
3. Add or edit the handcrafted Database Systems assets under `data/handcrafted/database_systems/`, then lint + ingest them:
   ```bash
   validate-handcrafted data/handcrafted/database_systems
  python scripts/ingest_handcrafted.py data/handcrafted/database_systems \
    outputs/world_model/state.sqlite --jsonl outputs/world_model/latest.jsonl
   ```
4. Initialize vendor submodules when ready:
   ```bash
   git submodule update --init --recursive
   ```

#### Teacher RLM path overrides

- The recursive teacher loop expects the vendored RLM package under `vendor/rlm`. If you want to test against a different checkout (for example, a local branch with experimental prompts), set the `COURSEGEN_VENDOR_RLM_PATH` environment variable to the directory that contains the `rlm/` package before launching the CLI:
  ```bash
  export COURSEGEN_VENDOR_RLM_PATH=$HOME/src/rlm
  python apps/orchestrator/run_poc.py --constraints ...
  ```
- Leaving the variable unset keeps the default behaviour (importing from `vendor/rlm`). Either way, the orchestrator automatically injects helper hooks into the REPL namespace—no manual `sys.path` surgery required.

### Model configuration & OpenAI credentials

- The `models` block inside `config/pipeline.yaml` (or `config/model_config.yaml`) can now use either the legacy flat form (`teacher_model`, `ta_model`, …) or the nested form:
  ```yaml
  models:
    teacher:
      provider: openai
      model: gpt-4.1
      api_key_env: OPENAI_API_KEY_TEACHER  # optional override
    ta:
      provider: openai
      model: gpt-4o-mini
      temperature: 0.1
    student:
      provider: openai
      model: gpt-4o-mini
  ```
- Per-role credentials are resolved in this order: the optional `api_key_env`, `OPENAI_API_KEY_<ROLE>` (e.g., `OPENAI_API_KEY_TA`), and finally the global `OPENAI_API_KEY`. Custom API bases follow the same pattern via `api_base`, `api_base_env`, `OPENAI_API_BASE_<ROLE>`, or `OPENAI_API_BASE`.
- The DSPy CodeAct registry now consumes those handles directly: Plan/Lecture/Citation programs automatically run with the TA handle, so you shouldn’t reconfigure `dspy.settings` inside agent code. Future student-facing CodeAct programs will draw from the `student` handle the same way.
- Any extra fields supplied under a role (timeouts, organization IDs, etc.) are passed straight to `dspy.OpenAI`, so you can tune provider-specific knobs without touching code.

## Running the PoC CLI
### Quick start (apps/orchestrator entry point)
Use the minimal shim in `apps/orchestrator/run_poc.py` when you just want to point at constraints + concept data:
```bash
python apps/orchestrator/run_poc.py \
  --constraints config/course_config.yaml \
  --concepts data/handcrafted/database_systems \
  --notebook database-systems-poc \
  --ablations no_students
```
The shim auto-detects the repo root, forwards everything to `ccopilot.cli.run_poc`, and keeps the flag surface to the subset documented in AGENTS.md. Add `--output-dir /tmp/coursegen-run`, `--dry-run`, `--quiet`, or `--ingest-world-model` as needed; any supplied ablations map directly to `no_world_model`, `no_students`, and/or `no_recursion`. Both this shim and the canonical `ccopilot.cli.run_poc` resolve relative paths (config, constraints, concept data, output dirs, world-model stores) against the `--repo-root` you pass, so you can launch the CLI from `/tmp` or a CI workspace without juggling `PYTHONPATH` or `cd`.

### Full CLI (coursegen-poc)
For advanced scenarios you can still invoke the canonical CLI exposed via the console script:
```bash
coursegen-poc --config config/pipeline.yaml --dry-run
```
Pass `--ingest-world-model` if you want the CLI to rebuild `outputs/world_model/state.sqlite` from `data/handcrafted/database_systems/`; otherwise the snapshot is auto-generated the first time it’s missing.

### Artifact outputs
Regardless of the entry point, the pipeline emits:
- `outputs/course_plan.md`
- `outputs/lectures/module_01.md`
- `outputs/evals/run-<timestamp>.jsonl`
- `outputs/provenance/run-<timestamp>.jsonl`
- `outputs/artifacts/run-<timestamp>-highlights.json` (concept/timeline slices powering the stub plan/lecture). When `--ablations` includes `no_world_model`, this file still exists but is derived from the handcrafted dataset instead of SQLite; the manifest’s `highlight_source` flag indicates which path produced it.

After every non-dry run the CLI also prints a short evaluation summary (overall score plus rubric pass/fail). If the student graders are disabled or missing, it reports that status instead of a score so operators immediately know why no grade was recorded. Highlight hints now spell out the source: `[highlights] saved to …` when the world model is active and `[highlights] (dataset) saved to …` when the `no_world_model` ablation forces the handcrafted fallback. Pass `--quiet` when scripting to suppress these `[eval]` / `[highlights]` hints while still writing every artifact.

Notebook exports pull their defaults from environment variables that `coursegen-poc` now sets during bootstrap: `OPEN_NOTEBOOK_API_BASE`, `OPEN_NOTEBOOK_API_KEY`, and `OPEN_NOTEBOOK_SLUG`. The CodeAct `push_notebook_section` tool will fall back to these values whenever the orchestrator does not pass explicit overrides, so make sure the config’s `notebook` section is filled in before running against a real instance. If you intentionally run without a live Open Notebook API, set `OPEN_NOTEBOOK_EXPORT_DIR=/path/to/exports` to opt into offline `.jsonl` exports; set `OPEN_NOTEBOOK_EXPORT_MIRROR=1` to mirror every API push to disk for auditing. Pass `--skip-notebook-create` (or set `OPEN_NOTEBOOK_AUTO_CREATE=0`) when you don’t have permission to create notebooks; otherwise the publisher calls the API once per run to ensure the slug exists and records the outcome as a “preflight” entry in the manifest. Each course plan and lecture is automatically chunked into notebook-friendly slices (≤5 plan sections, ≤3 lecture sections) before publishing so Open Notebook receives concise, cited notes. A dedicated FastAPI mock + httpx transport now lives in `tests/mocks/notebook_api.py`—use the `NotebookAPIMock.patch_open_notebook_client()` helper in tests such as `tests/test_pipeline_runtime.py`, `tests/test_cli_run_poc.py`, and `tests/test_open_notebook_tools.py` to exercise the full pipeline without an external server while still capturing note IDs. The CLI’s `[notebook]` hint now mirrors the manifest metadata via `notebook_export_summary`: successful pushes list the exported note IDs (or queued export paths when offline) so you can jump straight into the Notebook or debug failed attempts without opening the manifest.

### Running the grader CLI

You can re-run the lightweight student graders without invoking the full orchestrator via:

```bash
python -m apps.orchestrator.eval_loop --artifacts-dir outputs --lectures-dir lectures --rubric evals/rubrics.yaml
```

Add `--quiet` when you only care about the JSONL output under `outputs/evaluations/` and don’t want the console summary; other options (like `--required-source`) map 1:1 with the orchestrator’s grading hooks.

### Portal backend + shadcn UI

A minimal observability surface now lives under `apps/portal_backend` (FastAPI) and `frontend/` (Next.js + shadcn/ui). It reads the manifests that `coursegen-poc` emits under `outputs/artifacts` and exposes them as a small dashboard.

1. Start the API (defaults to `http://localhost:8001` but honors `PORTAL_OUTPUTS_DIR` and `PORTAL_NOTEBOOK_SLUG`). It now exposes `GET /runs/latest` and `GET /runs/{run_id}/notebook-exports` so the UI (or scripts) can fetch the most recent run + sanitized Notebook export metadata directly. All file-serving helpers are restricted to the configured `outputs/` directory to avoid path traversal through manifests:
   ```bash
   uvicorn apps.portal_backend.main:app --reload --port 8001
   ```
2. Install FE deps and launch the Next.js dev server (uses `NEXT_PUBLIC_PORTAL_API_BASE`, defaulting to `http://localhost:8001`):
   ```bash
   cd frontend
   pnpm install   # npm/yarn also work
   pnpm dev
   ```
3. Visit `http://localhost:3000` to see the latest run summary, highlight slices (badge indicates `World model` vs `Dataset fallback`), rubric scores, **teacher trace summary**, Notebook exports, and deep links to each historical run (e.g., `/runs/<run_id>`). The UI fetches `/runs/latest` on load, so re-run the CLI to refresh data.

Teacher trace JSON files (`outputs/logs/teacher-trace-*.json`) are now linked directly from the portal. The card shows the latest summary/action count and offers a download link for deeper inspection of the Teacher RLM loop.

Optional env vars:
- `NEXT_PUBLIC_NOTEBOOK_BASE` — base URL of your Open Notebook instance; combined with `OPEN_NOTEBOOK_SLUG` (or `PORTAL_NOTEBOOK_SLUG`) for the “Open Notebook” button.
- `NEXT_PUBLIC_TRIGGER_RUN_URL` — link to whatever automation you use to kick off a new orchestrator run (defaults to `#`).

## Development Workflow
- Use **bd (beads)** for issue tracking (`bd ready --json`, `bd update <id> --status in_progress`).
- Communicate/coordinate via **MCP Agent Mail**; file reservations prevent stomping each other (see `AGENTS.md`).
- Store planning artifacts under `history/` to keep the repo root clean.
- Inspect the handcrafted world model anytime with `python scripts/query_world_model.py concepts --topic "transactions"` (the CLI also supports `timeline` and `claims` subcommands) before running the orchestrator.
- `pytest` is scoped to `tests/` by default so vendor/rlm suites that depend on optional packages don’t fail local runs. To exercise vendor tests manually, run `PYTHONPATH=$PWD pytest vendor/rlm/tests` after installing the required extras.
- Workstreams:
  - **A:** Handcrafted dataset + world-model ingestion (issue `ccopilot-o78`).
  - **B:** Orchestrator CLI + CodeAct sandbox (issue `ccopilot-syy`).

Refer to `docs/PLAN.md`, `docs/PoC.md`, and `docs/ARCHITECTURE.md` for detailed acceptance criteria.

## World-Model Tooling
1. **Validate inputs** – `validate-handcrafted data/handcrafted/database_systems` (Typer CLI) fails fast when authors/papers/concepts/timeline/quiz rows drift out of sync. Run this before committing dataset edits.
2. **Rebuild snapshots** – `python scripts/ingest_handcrafted.py data/handcrafted/database_systems outputs/world_model/state.sqlite --jsonl outputs/world_model/snapshot.jsonl` regenerates both the SQLite store and a JSON Lines dump. You can also pass `--ingest-world-model` to `coursegen-poc` to chain validation + ingest before the orchestrator runs.
3. **Inspect data** – `wm-inspect concepts --store outputs/world_model/state.sqlite --topic transaction` (plus `timeline`, `claims`, `papers`, `authors`, `definitions`, `graph`, and the newer `artifacts` command) renders quick JSON tables without opening SQLite. Useful for debugging prompts and CodeAct tools. Pass `wm-inspect artifacts --type quiz_bank` (or `course_outline`) to see just that class of assets.

See `docs/WORLD_MODEL_TOOLING.md` for a full walkthrough (dataset layout, provenance expectations, troubleshooting tips).

## Testing
- Dataset + CLI coverage lives in `tests/test_handcrafted_loader.py`, `tests/test_cli_run_poc.py`, and `tests/test_query_world_model.py`. Run them with `PYTHONPATH=$PWD pytest` before shipping changes to the world-model pipeline. The pytest configuration is limited to `tests/` so we don’t accidentally pull in vendor submodules that require extra dependencies.
