# ChartreuseStone – CourseGen PoC Game Plan (2025-11-11)

## Context
- Read `docs/PLAN.md` + `docs/PoC.md` and synced on PoC scope (Teacher RLM orchestrating TA CodeAct agents across a Database Systems world model and publishing to Open Notebook).
- `bd ready --json` currently surfaces two ready items: `ccopilot-o78` (handcrafted DB systems knowledge assets) and `ccopilot-syy` (run_poc orchestrator + eval hooks).
- Repository root does _not_ currently contain a `.progress` file (only sibling repos `../courses` and `../taxonomy` do). Keeping planning artifacts under `history/` per AGENTS.md guidance until a shared `.progress` reappears.
- I claimed `ccopilot-syy` (`bd update ccopilot-syy --status in_progress`). Waiting on file-reservation overlap (GreenDog + OrangeHill currently hold `apps/**` + `config/**`).

## Proposed Workstream Split

### Workstream A – World Model + Data Authoring (`ccopilot-o78`)
Owner: _Need volunteer (RedCastle or RedHill would be great)._  Reviewer: ChartreuseStone (once orchestrator mocks wired).
Deliverables:
1. `data/handcrafted/database_systems/` populated with taxonomy, concepts, timeline, papers, authors, quiz_bank, rubrics (per `docs/PLAN.md §4.1/§4.4/§9`).
2. `world_model/schema.sql` + ingestion script (e.g., `scripts/ingest_handcrafted.py`) to hydrate SQLite/JSON artifact + snapshot under `outputs/world_model/`.
3. Evaluation assets: `evals/rubrics.yaml`, `evals/checklists.yaml`, `outputs/student_runs/*.jsonl` placeholders.
4. Documented seeds for the grader/mutator loop (quiz alignment + rubric mapping) so orchestrator can call into deterministic checks.
Dependencies: none besides docs; ideally ready before orchestrator tries to consume real data.

### Workstream B – RLM Orchestrator + CLI (`ccopilot-syy`)
Owner: ChartreuseStone (coord).  Reviewer: whoever is free.
Steps (rough order):
1. **Repo scaffolding** – create `apps/orchestrator/` (teacher, TA roles, students), `apps/codeact/` (tool registry + DSPy program wiring), `config/` (course + model configs), `outputs/` (course_plan, lectures, eval logs).
2. **CodeAct tool registry** – wrap WM CRUD, DuckDB/SQLite queries, bibliographic lookups, Open Notebook client stubs (pure functions per CodeAct requirements).
3. **Teacher loop & CLI** – `python apps/orchestrator/run_poc.py --constraints config/course_config.yaml --concepts data/... --notebook database-systems-poc [--ablation ...]` should orchestrate: ingest → plan → lecture → students → Notebook export, with toggles defined in config.
4. **Evaluation hooks** – integrate graders/students (simulate from JSON rubrics), persist `outputs/evals/*.jsonl`, and expose ablation flags (no recursion/students/world model).
5. **Publishing** – minimal Open Notebook SDK wrapper under `sandbox/tools_open_notebook.py` + ability to push plan/lecture artifacts.
Dependencies: needs data schema + sample records (Workstream A); can mock until ready.

### Shared TODOs / Sequencing
1. Initialize submodules (`vendor/rlm`, `vendor/open-notebook`) and pin SHAs.
2. Align on config format (`config/course_config.yaml`, `config/model_config.yaml`, `constraints.yaml`).
3. Decide on provenance/log layout (maybe `outputs/provenance/run-<timestamp>.jsonl`).
4. Once both workstreams land, schedule joint E2E test + ablation run.

## Coordination Notes / Blockers
- Unable to deliver the above via Agent Mail right now: `reply_message` to onboarding thread fails because OrangeHill currently holds an exclusive reservation on `agents/**` (blocks writes to `agents/ChartreuseStone/outbox`). I’ll retry once their reservation expires (12:03 UTC) or they release it.
- File reservations: my request for `apps/**` + `config/**` conflicts with existing locks (GreenDog + OrangeHill). I’ll avoid editing there until we coordinate or their holds expire (~12:01–12:03 UTC). In the meantime I’m preparing mocks + layout docs.

## Next Immediate Actions (ChartreuseStone)
1. Retry Agent Mail ping when `agents/**` lock clears; share this plan + confirm owners.
2. Once `apps/**` is free, scaffold the orchestrator + CLI skeleton tied to `ccopilot-syy`.
3. Document interface contracts for Workstream A ↔ B (expected file shapes, tool signatures) so data authors know what to produce.

## Update – 2025-11-11T10:45Z
- Authored the initial Database Systems dataset (taxonomy, concepts, timeline, papers, authors, quiz bank, citations) with stable IDs matching the existing course outline.
- Implemented a deterministic ingestion pipeline (`scripts/ingest_handcrafted.py`) that loads the handcrafted assets into `world_model/state.sqlite` and emits `outputs/world_model/latest.jsonl` for inspections.
- Latest snapshot stats: 23 authors, 22 papers, 30 concepts, 14 timeline observations, 6 quiz items. All concepts reference canonical sources recognised by `papers.csv`.
- Next: plumb the populated SQLite + JSONL artifacts into the CodeAct tools so TA roles can query real data (plan step #3).

## Update – 2025-11-11T11:08Z
- Extended `scripts/ingest_handcrafted.py` so `graph.yaml` edges populate `relationships` (relation types now carry descriptions/citations) and `definitions.yaml` statements become claim rows with provenance payloads. Re-ran the ingest: 30 concepts, 41 parent/prereq edges, 14 graph edges, 39 claims, 14 timeline observations.
- Refresh command: `python scripts/ingest_handcrafted.py data/handcrafted/database_systems world_model/state.sqlite --jsonl outputs/world_model/latest.jsonl` (also documented in README).
- Next for bd-ccopilot-o78: keep the wm_* adapters in sync with any schema tweaks from other agents and add lightweight tests around the ingestion helpers once the current reservations on `tests/` clear.
- Added a README note pointing folks to `scripts/query_world_model.py` (concept/timeline/claims subcommands) so everyone can inspect the ingested graph before running the orchestrator.
- Updated pipeline bootstrap to verify the handcrafted dataset exists and auto-ingest `world_model/state.sqlite` whenever the snapshot is missing (or when `--ingest-world-model` is passed). Added README guidance for the new CLI flag.
- New bead `ccopilot-us9`: scoping default `pytest` runs to `tests/` so vendor dependencies (surrealdb/ai_prompter) don’t break local/CI workflows. Will update `pyproject.toml` and README once done.
- Tightened `scripts/handcrafted_loader._load_csv` to raise when required CSVs are missing, so dataset validation can’t silently succeed with empty authors/papers/timeline files.
- Expanded the CodeAct registry (`apps/orchestrator/codeact_registry.py`) to surface `search_events` + `lookup_paper` so DSPy programs can query the world-model timeline and citation metadata. Added regression coverage in `tests/test_codeact_registry.py`.
- Extended `scripts/query_world_model.py` (wm-inspect CLI) with `papers` + `authors` subcommands, backed by helper query functions. Added tests in `tests/test_query_world_model.py` to cover the new queries.
