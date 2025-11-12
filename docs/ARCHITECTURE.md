# CourseGen PoC – Architecture & Interfaces (v0)

_Updated: 2025-11-11 by ChartreuseStone._  This document translates `docs/PLAN.md` and `docs/PoC.md` into concrete modules, file layouts, and contracts so Workstreams A (world model/data) and B (orchestrator) can build in parallel. **Note:** the user-facing CLI currently lives under `ccopilot/cli/run_poc.py` and is exposed via `python -m ccopilot.cli.run_poc`.

## 1. Directory Layout (target)

```
apps/
  orchestrator/
    __init__.py
    run_poc.py                 # CLI entry point
    teacher.py                 # Teacher RLM driver
    ta_roles/
      __init__.py
      syllabus_designer.py
      lecture_author.py
      librarian.py
      student_ops.py           # graders + mutation ops
    shared_state.py            # wrappers over WM snapshot
  codeact/
    __init__.py
    tools_registry.py          # pure tool catalog (Python functions)
    signatures.py              # DSPy signatures per tool/program
    programs.py                # CodeAct programs (PlanCourse, DraftLecture,...)
config/
  course_config.yaml
  model_config.yaml
  constraints.yaml
  ablations.yaml              # optional switches for CLI
world_model/
  schema.sql
  adapters.py                # helper queries/views for tools
  snapshots/
    <timestamp>.sqlite
    <timestamp>.jsonl
scripts/
  ingest_handcrafted.py
  eval_loop.py
vendor/
  rlm/
  open-notebook/
outputs/
  course_plan.md
  lectures/
    module_01.md
  evals/
    run-<timestamp>.jsonl
  provenance/
    run-<timestamp>.jsonl
  artifacts/
    run-<timestamp>-highlights.json   # slice of concepts/timeline/citations powering the run
history/
  *.md (planning logs – ignored or pruned later)
```

## 2. Configuration Contracts

### 2.1 `config/course_config.yaml`
```yaml
course_name: "Database Systems"
level: "upper-undergrad"
audience_prereqs:
  - "Discrete math"
  - "Intro programming"
format: "10-week"
constraints:
  tone: "studio"
  required_sources:
    - "Codd1970"
    - "SystemR1976"
  forbidden_sources: []
learning_objectives:
  - id: LO1
    text: "Explain the relational model and relational algebra."
assessment_emphasis:
  projects: true
  quizzes: true
```

### 2.2 `config/model_config.yaml`
```yaml
models:
  teacher: {provider: openai, model: "gpt-4.1"}
  ta: {provider: openai, model: "gpt-4o-mini"}
  students: {provider: openai, model: "gpt-4o-mini"}
codeact:
  max_iters: 5
  temperature: 0.2
  toolset: ["wm_get", "wm_search", "run_sql", "push_notebook"]
ablation_defaults:
  disable_recursion: false
  disable_students: false
  disable_world_model: false
```

### 2.3 `config/constraints.yaml`
Used for quick overrides per run (e.g., level, scope, ablations) and merged inside `run_poc.py` before dispatching to teacher.

## 3. Data & World Model Interfaces

### 3.1 Raw handcrafted files (`data/handcrafted/database_systems/`)
- `taxonomy.yaml`
- `concepts.yaml`
- `timeline.csv`
- `papers.csv`, `authors.csv`
- `quiz_bank.json`
- `citations.yaml` (BibTeX or inline references)

### 3.2 SQLite schema (excerpt)
```sql
CREATE TABLE concept (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  level TEXT,
  parent_id TEXT REFERENCES concept(id)
);
CREATE TABLE paper (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  year INTEGER,
  venue TEXT,
  url TEXT
);
CREATE TABLE claim (
  id TEXT PRIMARY KEY,
  concept_id TEXT REFERENCES concept(id),
  paper_id TEXT REFERENCES paper(id),
  text TEXT,
  evidence JSON,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE timeline (
  id TEXT PRIMARY KEY,
  year INTEGER,
  summary TEXT,
  importance TEXT,
  related_concepts TEXT
);
```
Run `python scripts/ingest_handcrafted.py data/handcrafted/database_systems world_model/state.sqlite --jsonl outputs/world_model/latest.jsonl` to refresh the snapshot consumed by CodeAct tools.

### 3.3 Tool consumption format
- World model tools operate on SQLite file; they return dictionaries (`list[dict[str, Any]]`) ready for CodeAct JSON serialization.
- `outputs/world_model/latest.jsonl` mirrors inserted nodes/edges for provenance.
- `wm-inspect` (Typer CLI under `scripts/query_world_model.py`) exposes read-only views of the snapshot. Commands currently include `concepts`, `timeline`, `claims`, `papers`, `authors`, `definitions`, `graph`, and `artifacts` so developers can review relationships/definitions and see which quiz banks/course outlines were ingested without opening SQLite manually.
- `wm-inspect` (Typer CLI under `scripts/query_world_model.py`) exposes read-only views of the snapshot. Commands currently include `concepts`, `timeline`, `claims`, `papers`, `authors`, `definitions`, `graph`, and `artifacts` so developers can review relationships/definitions and see which quiz banks/course outlines were ingested without opening SQLite manually.

## 4. CodeAct Tool Signatures (initial set)

| Tool | Signature | Notes |
| --- | --- | --- |
| `wm_get_concepts` | `(topic: str, depth: int=1) -> list[Concept]` | BFS over taxonomy for module planning |
| `wm_search_events` | `(query: str) -> list[TimelineEvent]` | Filter timeline.csv/sqlite |
| `run_sql` | `(query: str) -> list[dict]` | Backed by DuckDB w/ curated CSVs |
| `lookup_paper` | `(paper_id: str) -> Paper` | Adds citation block |
| `record_claim` | `(concept_id: str, content: str, citations: list[str]) -> ClaimId` | Writes to WM snapshot |
| `push_notebook_section` | `(notebook: str, section: dict) -> dict` | REST call to vendor/open-notebook |
| `grade_module` | `(module_md: str, rubric_id: str) -> dict` | Wraps student graders |
| `list_claims` | `(concept_id: Optional[str]) -> list[Claim]` | Read-only view of previously recorded claims for grounding/explanations |
| `list_relationships` | `(concept_id: Optional[str]) -> list[Edge]` | Inspect prerequisite/graph edges for TA prompts |

All tools must be synchronous, side-effect free except for `record_claim` + `push_notebook_section` (which log to provenance + Notebook). CodeAct code cannot `import` arbitrary modules—provide everything through tool arguments.

## 5. Orchestrator Flow (RunPoC)

1. **Load configs** and ablations.
2. **Load/mount world model** snapshot (or stub if disabled).
3. **Teacher RLM** (apps/orchestrator/teacher.py):
   - Initialize REPL environment with handles: `use_codeact(program_name)`, `spawn_ta(role)`, `wm.*` helpers.
   - Stage 1: call `PlanCourse` CodeAct program (TA-Syllabus) to produce `course_plan.md` (persist + send to Notebook if enabled).
   - Stage 2: for first module, spawn TA combination (Reader, Author, Librarian) to draft `lectures/module_01.md`.
   - Stage 3: run `grade_module` student loop; if score < threshold, mutate prompts/policy and re-run (max 2 passes).
   - Stage 4: export plan + lecture via `push_notebook_section` and log run metadata.
4. **Evaluation hooks**: `apps/orchestrator/student_ops.py` collects quiz responses + rubric scores, writes to `outputs/evals/run-<ts>.jsonl`.
5. **Provenance + summary**: `outputs/provenance/run-<ts>.jsonl` includes tool call transcripts, seeds, ablations used, and a pointer to the world-model highlight artifact saved under `outputs/artifacts/run-<ts>-highlights.json`.
6. CLI returns exit code 0 on success, non-zero on failure, and prints (a) the evaluation summary (overall score + rubric pass/fail) whenever graders run and (b) the log path / reason when graders are skipped (dry run, `--ablations no_students`, missing rubrics). Pass `--quiet` when scripting to suppress the `[eval]`/`[highlights]` hints while still writing every artifact; the standalone grader CLI (`python -m apps.orchestrator.eval_loop`) exposes the same flag.
7. Notebook exports default to the environment variables populated during bootstrap: `OPEN_NOTEBOOK_API_BASE`, `OPEN_NOTEBOOK_API_KEY`, and `OPEN_NOTEBOOK_SLUG` (all derived from `PipelineConfig.notebook`). CodeAct tools fall back to these values whenever the orchestrator does not pass explicit overrides, keeping CLI + tools in sync.

## 6. Interface Contracts Between Workstreams

| Producer | Artifact | Consumer |
| --- | --- | --- |
| Workstream A | `world_model/snapshots/latest.sqlite` + exported JSONL | CodeAct tools (`wm_get_*`, `run_sql`) |
| Workstream A | `data/handcrafted/…` raw files | `scripts/ingest_handcrafted.py` + ingestion tests |
| Workstream A | `evals/rubrics.yaml`, `quiz_bank.json` | `grade_module` + `student_ops.py` |
| Workstream B | `apps/codeact/tools_registry.py` tool stubs | Teacher + TA CodeAct programs |
| Workstream B | `outputs/course_plan.md`, `lectures/*.md` | Open Notebook exporter |

Versioning: each ingestion/export run writes a manifest `outputs/run-<ts>/manifest.json` capturing file hashes + config to satisfy reproducibility criteria.

## 7. Ablation Switch Behavior

CLI flag `--ablation <mode>` or YAML list toggles components:
- `students`: skip student graders/mutators; still log placeholder results.
- `world_model`: bypass SQLite + teach using only raw YAML (mock tool responses).
- `recursion`: run teacher in single-agent mode (no `spawn_ta`).
Each toggle must be reflected in `outputs/evals/...` (documented for acceptance tests).

## 8. Open Questions
- Precise list of TA roles for first PoC? (current assumption: SyllabusDesigner, LectureAuthor, Librarian, StudentOps.)
- How much of the notebook export should be synchronous vs. batched? (leaning synchronous per run.)
- Do we store Notebook IDs in `outputs/notebook_refs.json` for later diffing?

Please comment in Agent Mail (once the `agents/**` lock clears) or in a follow-up history note before editing major sections.
