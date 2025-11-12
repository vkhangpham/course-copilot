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
     world_model/state.sqlite --jsonl outputs/world_model/latest.jsonl
   ```
4. Initialize vendor submodules when ready:
   ```bash
   git submodule update --init --recursive
   ```

## Running the PoC CLI
With sample configs + placeholder data:
```bash
coursegen-poc --config config/pipeline.yaml --dry-run
```
Pass `--ingest-world-model` if you want the CLI to rebuild `world_model/state.sqlite` from `data/handcrafted/database_systems/`; otherwise the snapshot is auto-generated the first time it’s missing.
The stubbed pipeline emits:
- `outputs/course_plan.md`
- `outputs/lectures/module_01.md`
- `outputs/evals/run-<timestamp>.jsonl`
- `outputs/provenance/run-<timestamp>.jsonl`
- `outputs/artifacts/run-<timestamp>-highlights.json` (world-model concept/timeline slices powering the stub plan/lecture)

After every non-dry run the CLI also prints a short evaluation summary (overall score plus rubric pass/fail). If the student graders are disabled or missing, it reports that status instead of a score so operators immediately know why no grade was recorded. Pass `--quiet` when scripting to suppress these `[eval]` / `[highlights]` hints while still writing every artifact.

Notebook exports pull their defaults from environment variables that `coursegen-poc` now sets during bootstrap: `OPEN_NOTEBOOK_API_BASE`, `OPEN_NOTEBOOK_API_KEY`, and `OPEN_NOTEBOOK_SLUG`. The CodeAct `push_notebook_section` tool will fall back to these values whenever the orchestrator does not pass explicit overrides, so make sure the config’s `notebook` section is filled in before running against a real instance.

### Running the grader CLI

You can re-run the lightweight student graders without invoking the full orchestrator via:

```bash
python -m apps.orchestrator.eval_loop --artifacts-dir outputs --lectures-dir lectures --rubric evals/rubrics.yaml
```

Add `--quiet` when you only care about the JSONL output under `outputs/evaluations/` and don’t want the console summary; other options (like `--required-source`) map 1:1 with the orchestrator’s grading hooks.

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
2. **Rebuild snapshots** – `python scripts/ingest_handcrafted.py data/handcrafted/database_systems world_model/state.sqlite --jsonl outputs/world_model/snapshot.jsonl` regenerates both the SQLite store and a JSON Lines dump. You can also pass `--ingest-world-model` to `coursegen-poc` to chain validation + ingest before the orchestrator runs.
3. **Inspect data** – `wm-inspect concepts --store world_model/state.sqlite --topic transaction` (plus `timeline`, `claims`, `papers`, `authors`, `definitions`, `graph`, and the newer `artifacts` command) renders quick JSON tables without opening SQLite. Useful for debugging prompts and CodeAct tools. Pass `wm-inspect artifacts --type quiz_bank` (or `course_outline`) to see just that class of assets.

See `docs/WORLD_MODEL_TOOLING.md` for a full walkthrough (dataset layout, provenance expectations, troubleshooting tips).

## Testing
- Dataset + CLI coverage lives in `tests/test_handcrafted_loader.py`, `tests/test_cli_run_poc.py`, and `tests/test_query_world_model.py`. Run them with `PYTHONPATH=$PWD pytest` before shipping changes to the world-model pipeline. The pytest configuration is limited to `tests/` so we don’t accidentally pull in vendor submodules that require extra dependencies.
