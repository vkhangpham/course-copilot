# PRD · PoC: World‑Model + Multi‑Recursive Agents for Course Generation (Concept: _Database Systems_)

## 0) Goal & Success Criteria

**Goal.** Demonstrate that a teacher LLM (RLM) can orchestrate T/A sub‑agents inside a sandbox (DSPy CodeAct) to: (1) explore a hand‑engineered _Database Systems_ world model; (2) synthesize a **course plan**; (3) generate a **lecture/study guide**; (4) self‑assess with “student” graders; and (5) ship the final content into **Open Notebook** (NotebookLM‑like) as the publishing surface.

**What “done” looks like (acceptance).**

- A single CLI command runs the full pipeline from inputs → Open Notebook notebook with:
  - **Course plan** (weeks/modules, learning objectives).
  - **Lecture/study guide** (at least one module rendered with sources/citations).
  - **Artifacts & logs:** world‑model graph snapshot, agent execution trace, student scores, and provenance.

- **Reproducibility:** one seed/config produces the same outline and ≥80% “student” comprehension on a fixed quiz bank.
- **Ablation toggles:** can disable (a) recursive sub‑agents, (b) students, or (c) world‑model memory to show each component’s effect.

---

## 1) Architectural Overview (how pieces fit)

**Core principles from the research you cited:**

- **RLM**: treat the prompt/context as _state_ in an environment; allow the LM to **spawn sub‑LM calls** and manipulate context via a REPL. We’ll use the minimal RLM that exposes `RLM_REPL.completion()` and depth‑1 subcalls, extending it with our tools. ([Alex L. Zhang][1])
- _Tip:_ The teacher orchestrator imports `rlm.rlm_repl` from the vendored `vendor/rlm` checkout by default. If you are iterating on a different clone (for example, a local fork with experimental prompts), export `COURSEGEN_VENDOR_RLM_PATH=/absolute/path/to/rlm` before running the CLI so bootstrap adds that directory to `sys.path`.
- **CodeAct as the one sandbox**: **all “thinking with code” + tool use** happens through **DSPy CodeAct**. CodeAct takes a **signature** and **pure‑function tools**, iterates, emits code, executes, and returns results; it **does not import external libs**, so we wrap any library (DuckDB, graph ops, parsers) behind pure‑function tools. ([dspy.ai][2])
- **Kosmos world model**: maintain a **structured world model** as the shared state bus across agents (entities, claims, observations, tasks) with provenance; agents read/write through tools. ([arXiv][3])
- **Self‑Evolving Agents** loop (grader/mutator): create **“student” agents** that test understanding and drive mutation of materials; run improve→grade cycles. ([OpenAI Cookbook][4])
- **NotebookLM/Open Notebook** as _publisher_: after content stabilizes, ship into **Open Notebook** via its API/backend so the result is explorable as a notebook. ([GitHub][5])

**Repo layout (proposed within your PoC repo root):**

```
/agents/
  teacher_rlm.py              # wraps RLM_REPL; spawns T/As; orchestrates steps
  ta_roles.py                 # role prompts and capabilities for T/A types
  students.py                 # graders, QA students, rubric graders (LLM-judge)
/sandbox/                     # DSPy CodeAct program + tool registry
  tools_world_model.py        # pure tools to read/write world model (wrapping DB/graph)
  tools_data.py               # wrappers for DuckDB/SQLite, parsers, citation utilities
  tools_open_notebook.py      # minimal client to post sections to Open Notebook
  program_codeact.py          # dspy.CodeAct(...) definitions per role/task
/world_model/
  schema.sql                  # SQLite schema for nodes/edges/provenance
  adapters.py                 # serialization + views; timeline→entities, etc.
/data/handcrafted/database_systems/
  taxonomy.yaml
  timeline.csv
  papers.csv
  authors.csv
  concepts.yaml
  quiz_bank.json
/evals/
  rubrics.yaml
  checklists.yaml
/ui/
  web/                        # simple Next.js or reuse Open Notebook front-end linkouts
/config/
  course_config.yaml          # level, focus, preferences, constraints
  model_config.yaml           # base LM ids, temperatures, depth, budgets
scripts/
  run_poc.py                  # end-to-end runner
vendor/
  rlm/                        # submodule: your fork; upstream: alexzhang13/rlm
  open-notebook/              # submodule: your fork; upstream: lfnovo/open-notebook
```

---

## 2) Inputs & Outputs (for this PoC)

**Inputs.**

- **World data (hand‑engineered)** for _Database Systems_: taxonomy, concepts, relationships, key papers (Codd 1970; System R; Postgres; ARIES; CAP; Spanner…), authors, timeline; course constraints (level, focus), plus a small **quiz bank** aligned with LOs.
- **Tools** (CodeAct‑wrapped): world‑model CRUD, paper lookups (from local CSV), timeline queries, SQL runners (via DuckDB/SQLite), outline validators, citation verifier.

**Outputs.**

- **Course plan** (weeks/modules; LOs per module; reading list).
- **Lecture/study guide** for ≥1 module (headings, explanations, worked examples, checks for understanding, citations to papers).
- **Student eval report** (scores, failure cases, mutation history).
- **Open Notebook** notebook created/updated with plan + lecture content and attached sources. ([GitHub][5])

---

## 3) Step‑by‑Step Implementation Plan

### Phase A — Environment & Submodules

1. **Add submodules** (you already cloned—confirm remotes and pins):

   ```bash
   git submodule add https://github.com/vkhangpham/rlm vendor/rlm
   git submodule add https://github.com/vkhangpham/open-notebook vendor/open-notebook
   git submodule update --init --recursive
   ```

   For upstream reference APIs we rely on:
   - **RLM minimal** (`rlm/rlm_repl.py`, class **`RLM_REPL`**, method **`completion()`**) and `repl.py` (sub‑LM call). ([GitHub][6])
   - **Open Notebook** project structure (`/api`, `/open_notebook`, `/frontend`, `run_api.py`) for integration points. ([GitHub][5])

2. **Python env.**
  - Python 3.11, `pip install dspy duckdb sqlite-utils pydantic fastapi uvicorn networkx orjson python-dotenv`.
  - `pip install -e vendor/rlm` if needed (or add to `PYTHONPATH`).
  - Add `.env` for API keys (OpenAI/Gemini if relevant), DB paths, Open Notebook API base. DSPy now reads per-role keys in order: `api_key_env` (from `config/model_config.yaml`), `OPENAI_API_KEY_<ROLE>`, and finally `OPENAI_API_KEY`. API bases follow the same pattern via `api_base` / `OPENAI_API_BASE_<ROLE>` / `OPENAI_API_BASE`. CodeAct factories are wired to those handles (PlanCourse/Lecture/Enforce use the TA handle today; future student programs draw from the student handle automatically).
  - The teacher RLM imports `rlm.rlm_repl` from the vendored checkout by default (`vendor/rlm` inside this repo). If you’re iterating on a separate clone or a local branch, export `COURSEGEN_VENDOR_RLM_PATH=/absolute/path/to/rlm_checkout` before running the CLI so the orchestrator adds that directory to `sys.path`.

3. **Model configs.** Use `/config/model_config.yaml` to set per-role providers/models (teacher/ta/student) plus optional API key/base env overrides. Temperatures/max tokens fall back to `default_temperature` / `default_max_tokens` if a role omits them.

---

### Phase B — World Model (central shared state)

**Schema.** Use **SQLite** as the store with a light graph overlay:

- `nodes(id, type, title, content_json, created_at)` — types: `Concept`, `Paper`, `Author`, `Claim`, `Task`, `LectureSection`, `QuizItem`, `Observation`.
- `edges(src_id, rel, dst_id)` — rels: `subconcept_of`, `written_by`, `supports`, `refutes`, `covers`, `evaluates`, `derived_from`.
- `provenance(id, subject_id, tool, code, inputs_json, outputs_json, lm_trace_json, timestamp)`.

**Interfaces (all via CodeAct tools, not direct imports):**

- `wm_get(node_id|query)`, `wm_add(node|edge)`, `wm_link(src, rel, dst)`, `wm_claim(text, cites=[paper_ids])`,
- `wm_view.tl(concept_id)` (timeline), `wm_view.taxonomy(concept_id)`,
- `wm_snapshot()` (for UI/debug/export).

This mirrors Kosmos’ notion of a **structured world model shared across agents**; we’re simplifying entity types for a course domain. ([arXiv][3])

**Data ingestion (hand engineering).**

- Convert `taxonomy.yaml`, `timeline.csv`, `papers.csv`, `authors.csv` into nodes/edges (script: `scripts/ingest_handcrafted.py`).
- Validate edges (no dangling ids), build a few **pre‑linked “claims”** with source papers to seed grounded content.

---

### Phase C — DSPy CodeAct Sandbox (the only code/exec surface)

**Why CodeAct:** it enforces “**tools only**” code (no arbitrary imports); so we **wrap external libs** into our pure functions (tools). Constraints & usage come straight from DSPy docs: `dspy.CodeAct(signature, tools, max_iters=…)` and **pure function only**, **no external imports** in generated code. ([dspy.ai][2])

**Tooling sets (pure functions):**

- **World‑model tools:** `get_concepts()`, `get_papers()`, `link()`, `record_claim()`, `search_timeline(...)`, each internally uses SQLite/NetworkX but **exposes pure signatures** to CodeAct.
- **Data tools:** `run_sql(sql: str) -> rows` (wrap DuckDB), `render_table(rows) -> md`, `bib_lookup(paper_id) -> bibtex`, `check_citations(text) -> report`.
- **Synthesis tools:** `outline_from_taxonomy(level, focus) -> outline`, `lo_from_outline(outline) -> objectives`, `lecture_scaffold(module) -> sections`.
- **Open‑Notebook tools:** `on_create_notebook(title) -> notebook_id`, `on_add_section(notebook_id, title, md) -> section_id`. (We connect to Open Notebook’s API backend; see repo structure with `/api`, `run_api.py` to confirm FastAPI endpoints or add a thin adapter in our PoC.) ([GitHub][5])

**CodeAct programs (by role/task):**

- `program_codeact.py` defines DSPy programs for tasks like `PlanCourse`, `DraftLectureSection`, `EnforceCitations`, each with a **Signature** and `tools=[…]`.

---

### Phase D — RLM Teacher + Recursive T/As

**Teacher orchestration (RLM).**

- **Wrap `RLM_REPL`** (from `vendor/rlm`) in `teacher_rlm.py`. The **environment** exposes a small Python API to the LM:
  - `use_codeact(program_name, **kwargs)` → runs the right CodeAct program with given tools.
  - `spawn_ta(role, task_spec)` → calls a **sub‑LM** (depth‑1) with a role‑conditioned system prompt; sub‑LM **also** uses `use_codeact` for any tool/code.
  - `wm.observe()` / `wm.commit()` for quick environment reads/writes (under the hood these call the CodeAct tools, keeping **one sandbox** policy).

> The minimal RLM provides `completion()` and a depth‑1 subcall pattern; we implement the “sub‑agent” convention with role‑wrapped **sub‑LM calls** and the same sandbox entrypoints. ([GitHub][6])

**TA roles (examples).**

- **TA‑Syllabus**: transform taxonomy + constraints into **module plan**; ensures **LOs** are measurable.
- **TA‑Reader**: pulls paper abstracts/claims from `papers.csv` and writes **grounded claims** into the world model.
- **TA‑Author**: drafts **lecture sections** with examples and inline citations; calls `EnforceCitations` tool to validate.
- **TA‑Assessment**: builds **quizzes** from LOs and materials (fills `/data/…/quiz_bank.json` if missing).
- **TA‑Librarian**: final **Open Notebook** export (creates notebook, sections, attaches sources).

**Teacher loop (high‑level pseudo‑flow).**

1. `spawn_ta('TA-Syllabus', task=build_outline_from_taxonomy)` → `PlanCourse` → save to WM.
2. For each module:
   a) `spawn_ta('TA-Reader', task=mine_claims_for_module)` → ingest claims.
   b) `spawn_ta('TA-Author', task=draft_lecture_sections)` → draft MD with citations.
   c) Trigger **students** (Phase E) and, if needed, `spawn_ta('TA-Author', task=mutate_section_based_on_feedback)`.
3. `spawn_ta('TA-Librarian', task=publish_to_open_notebook)`.

---

### Phase E — “Students” (graders) & Mutation Loop

**Pattern from Self‑Evolving Agents.** Implement _students_ that read the draft, attempt quizzes, and grade with rubrics; _mutators_ revise content accordingly; iterate to a stop criterion. ([OpenAI Cookbook][4])

- **Student‑QA:** given module text + quiz bank, answers questions; we score exact/regex or simple heuristic.
- **Student‑Explainer:** attempts to re‑teach the section; grader checks **coherence**, **coverage of LOs**, **reading level**, and **citation grounding**.
- **Mutators (TA‑Author with a different “mutation” instruction set):**
  - _Refine‑clarity_, _Add‑worked‑example_, _Strengthen‑grounding_ (ensure every claim ties to `Paper` nodes), _Reorder‑for‑prereqs_.

**Stop conditions.** Two of: (i) ≥80% quiz pass, (ii) rubric score ≥ threshold, (iii) citations checker passes, or (iv) max iterations (e.g., 2).

> The “explore‑evaluate‑mutate” loop echoes **AlphaEvolve‑style** iterative improvement (generate, test, refine) you linked from mathematical exploration; we adapt it to pedagogy. ([arXiv][7])

---

### Phase F — Open Notebook (NotebookLM‑style) Export

- Spin up or point to your fork of **Open Notebook** (FastAPI + Next.js). From PoC we only need endpoints to **create a notebook** and **add sections** (or write a skinny `/api/import` in your fork to accept Markdown and optional metadata). Repo layout shows `/api`, `run_api.py`, `/open_notebook`, `/frontend` for reference. ([GitHub][5])
- CodeAct tools `on_create_notebook(...)` and `on_add_section(...)` POST to that API.
- Teacher triggers the export after student checks pass. For local development, set `OPEN_NOTEBOOK_EXPORT_DIR=/path/to/jsonl` to capture offline exports and `OPEN_NOTEBOOK_EXPORT_MIRROR=1` if you want the API path to double-write to disk. `OPEN_NOTEBOOK_API_BASE`, `OPEN_NOTEBOOK_API_KEY`, and `OPEN_NOTEBOOK_SLUG` are resolved from the pipeline config/CLI; overriding them via env lets you point the orchestrator at a dev stack without editing YAML. Use `--skip-notebook-create` (or `OPEN_NOTEBOOK_AUTO_CREATE=0`) when you want to disable the default “pre-flight” notebook creation step.
- NotebookPublisher chunks artifacts before shipping: the course plan is split into up to five sections and the current lecture into three sections so Open Notebook receives digestible notes with per-section citations. The manifest now records `notebook_export_summary` (success/skipped/error counts, note IDs, queued export paths) so the CLI and portal can report export health without scraping raw responses.
- A dedicated FastAPI mock + httpx transport now lives in `tests/mocks/notebook_api.py`. Use the `NotebookAPIMock.patch_open_notebook_client()` helper in integration tests (see `tests/test_pipeline_runtime.py`, `tests/test_cli_run_poc.py`, and `tests/test_open_notebook_tools.py`) to run the full pipeline against the mock API without a live server. This mock captures section IDs, enforces auth headers, and mirrors the offline export behavior so CLI hints and manifests include note IDs even in tests.

> For educators’ affordances of the NotebookLM paradigm, see applied discussions as context (grounded summarization, citations, podcast export, etc.), which our Open Notebook fork mirrors. ([NSUWorks][8])

---

## 4) Detailed Task List (with concrete references)

### 4.1 World Model & Data

- [ ] Define `schema.sql` and create DB.
- [ ] Write `scripts/ingest_handcrafted.py` to load:
  - `/data/.../taxonomy.yaml` → `Concept` nodes + `subconcept_of` edges.
  - `/data/.../timeline.csv` → `Observation` with timestamps; edges `covers`.
  - `/data/.../papers.csv`, `/authors.csv` → `Paper`, `Author`, `written_by`; join to concepts.

- [ ] Author **seed claims** (e.g., “Relational model formalized by Codd (1970) …”) linked to `Paper` ids.

### 4.2 CodeAct Sandbox

- [ ] Implement **pure tools** (module `sandbox/tools_world_model.py`, `.../tools_data.py`).
  - Example: `def run_sql(query: str) -> list[dict]:` internally uses DuckDB; returns rows; zero side‑effects.

- [ ] Define **DSPy CodeAct programs** in `sandbox/program_codeact.py`:
  - `PlanCourse`: `"constraints -> outline"` using `get_concepts`, `search_timeline`.
  - `DraftLectureSection`: `"module, claims -> md_section"` using `run_sql` (for examples), `bib_lookup`, `record_claim`.
  - `EnforceCitations`: `"md_section -> md_section"` using `check_citations`.

- [ ] Ensure **no non‑tool imports** in generated code per CodeAct rules. ([dspy.ai][2])

### 4.3 RLM Integration

- [ ] Vendor/wrap **`vendor/rlm/rlm/rlm_repl.py`** in `agents/teacher_rlm.py`:
  - Expose to the LM: `use_codeact`, `spawn_ta`, `wm_get`, `wm_link`, etc., as Python functions in the REPL namespace (this is exactly the RLM environment idiom). ([GitHub][6])

- [ ] TA roles in `agents/ta_roles.py` with **role prompts** and **tool whitelists** (each TA’s `use_codeact` calls a specific program).
- [ ] Compose the **teacher plan**: `build_outline → module loop (claims→draft→students→mutate) → export`.

### 4.4 Students & Mutation

- [ ] Implement **Student‑QA**: generates answers, scores against `quiz_bank.json`.
- [ ] Implement **LLM graders** with rubrics (`/evals/rubrics.yaml`).
- [ ] Implement **mutations** (operator prompts) and loop orchestration (max 2 passes).

> Design follows **Self‑Evolving Agents** modular retraining/evaluation loop (we reuse the _grader/mutator_ notion). ([OpenAI Cookbook][4])

### 4.5 Open Notebook Export

- [ ] Add `sandbox/tools_open_notebook.py`: HTTP client to your fork.
- [ ] In **Open Notebook** fork, add a _minimal_ `/api/import` if missing (FastAPI): `POST /import {title, sections:[{title, md, sources}]}` → creates notebook + sections. Repo shows `/api` and `run_api.py` entrypoint for API server. ([GitHub][5])

### 4.6 UI / Observability

- [ ] **Minimal web UI** (Next.js) or a simple **Streamlit** to display:
  - World‑model graph snapshot,
  - Agent trace (teacher→TAs, tool calls),
  - Student scores and stop reasons,
  - Link to the **Open Notebook** notebook.

- [ ] Log **provenance** of every tool call (code, inputs, outputs) to the `provenance` table.

---

## 5) End‑to‑End Flow (what actually happens)

1. **Ingest** the hand‑engineered _Database Systems_ data into the world model.
2. **Teacher (RLM)** starts with user constraints from `course_config.yaml`; calls `use_codeact("PlanCourse")` (TA‑Syllabus may run as a sub‑LM call) to produce an **outline** + LOs → persisted to WM. (RLM pattern: LM interacts with an environment, spawns sub‑calls.) ([Alex L. Zhang][1])
3. For each module:
   - **TA‑Reader** mines **claims** and associates **papers/authors** (grounding).
   - **TA‑Author** drafts **lecture sections** (MD), uses `EnforceCitations` to check every claim has a source.
   - **Students** run on the draft; if below threshold, **mutate** and re‑grade (AlphaEvolve‑style iterate‑and‑test, adapted to pedagogy). ([arXiv][7])

4. **TA‑Librarian** exports plan + lecture(s) to **Open Notebook** via API (create notebook, add sections). ([GitHub][5])
5. **UI** shows graph snapshot, trace, student outcomes, highlight slices, and a link to the notebook; highlight cards should clearly label the source (world model vs dataset fallback) so ablation runs are obvious at a glance.

---

## 6) Timelined Checklist (1–1.5 weeks of focused work)

**Day 1–2**

- World model schema + ingestion scripts; seed data authored.
- CodeAct tool wrappers (WM CRUD, DuckDB, citations); test locally with small signatures. ([dspy.ai][2])

**Day 3**

- Integrate RLM: expose `use_codeact` & `spawn_ta` in the REPL environment; run a dry “hello world” (teacher asks TA to fetch 3 key papers and record claims). ([GitHub][6])

**Day 4**

- Implement TA programs: PlanCourse, DraftLectureSection, EnforceCitations.
- Implement Student‑QA & rubric grader; add one mutation operator.

**Day 5**

- End‑to‑end single‑module run; log provenance; tune stop conditions.

**Day 6**

- Open Notebook API adapter + export; verify notebook appears with sections. ([GitHub][5])

**Day 7**

- UI, doc polish, and 3 ablations (no recursion / no students / no world model). When `no_world_model` is active, highlight exports still land in `outputs/artifacts/run-*-highlights.json` but should be marked `highlight_source="dataset"` and surfaced as such in CLI + portal so reviewers can prove the ablation took effect.

#### Progress log

- *2025-11-14:* `apps/orchestrator/run_poc.py` now resolves a hidden `--repo-root`, only exposes `--constraints`, `--concepts`, `--notebook`, and optional `--ablations`, and forwards the detected science-config file before calling the canonical CLI (`--concepts` / `--concept` now share a single flag). Tracked in bead `ccopilot-fcf3`.
- *2025-11-14:* `ccopilot.cli.run_poc` defaults `--repo-root` to the repository root constant so automation can invoke the console script from any directory, the quick-start docs now explain the shim vs full CLI surface, and the parser test confirms the default path.
- *2025-11-14:* `pytest tests/test_apps_run_poc.py tests/test_cli_run_poc.py` plus the focused `pytest tests/test_cli_run_poc.py -q` runs verify the CLI changes keep existing behaviours intact.

---

## 7) Risks & Mitigations

- **CodeAct tool constraints** (no external imports in generated code) → **wrap all libs** as pure tools; pass every dependent function explicitly, per docs. ([dspy.ai][2])
- **RLM depth & control**: minimal repo supports depth‑1; that’s sufficient for PoC. If we need deeper recursion, the repo suggests replacing `Sub_RLM` with `RLM_REPL` (careful with nested REPL). ([GitHub][6])
- **Open Notebook API surface**: if an import endpoint is not readily available, add a **thin FastAPI route** in your fork under `/api`. Repo shows `/api` directory and `run_api.py` entrypoint. ([GitHub][5])
- **Grounding quality**: rely on **seeded claims** + strict citation checkers; student‑grader detects gaps and triggers **Strengthen‑grounding** mutation. (Pattern inspired by **Kosmos** “world model + citations” and **NotebookLM** “grounded synthesis”.) ([arXiv][3])

---

## 8) Concrete Interfaces (sketch)

**Teacher RLM environment (available functions in REPL):**

```python
# Provided to RLM_REPL env:
def use_codeact(program: str, **kwargs) -> dict: ...
def spawn_ta(role: str, task: dict) -> dict: ...  # sub-LM call with role prompt
def wm_get(query: str) -> dict: ...
def wm_add(node_or_edge: dict) -> str: ...
def wm_link(src: str, rel: str, dst: str) -> None: ...
```

> The minimal RLM repo exposes `RLM_REPL.completion()` which we call after injecting the above into the REPL environment. ([GitHub][6])

**DSPy CodeAct program example:**

```python
# PlanCourse signature (sketch)
sig = "constraints -> outline"
act = dspy.CodeAct(sig, tools=[get_concepts, search_timeline, outline_from_taxonomy], max_iters=5)
result = act(constraints=course_cfg)
```

> This mirrors the CodeAct API and “tools-only” execution pattern. ([dspy.ai][2])

---

## 9) Data You Should Hand‑Engineer Now (for _Database Systems_)

1. **taxonomy.yaml** — `Databases` → `Relational model`, `SQL`, `Transactions/ACID`, `Concurrency control`, `Indexing`, `Query optimization`, `Storage`, `Logging/Recovery (ARIES)`, `Distributed DB`, `CAP`, `NoSQL`, `NewSQL`.
2. **timeline.csv** — key milestones (Codd 1970; System R; Postgres; ARIES; MapReduce, Bigtable, Spanner; modern cloud warehouses).
3. **papers.csv / authors.csv** — classic and modern references with BibTeX keys.
4. **concepts.yaml** — canonical definitions + prerequisites.
5. **quiz_bank.json** — 10–20 items covering core LOs (definitions, why/when, small SQL tasks).

_(Exact references are standard; the focus here is structure and linkage to claims.)_

---

## 10) What We’re Borrowing & Why (explicit ties to the research)

- **RLM** gives us a **recursive orchestration** model where the LM manages context in a REPL‑like environment and can spawn sub‑LMs—exactly our teacher→T/A flow. ([Alex L. Zhang][1])
- **DSPy CodeAct** yields a **safe, tool‑first sandbox**: LMs produce code that only uses our vetted tools; we wrap external libraries and world‑model access into pure functions (no imports). ([dspy.ai][2])
- **Kosmos** informs the **world model**: a structured, shared memory where data analysis/literature claims and tasks interlock, plus **citation discipline**. ([arXiv][3])
- **Self‑Evolving Agents** supplies the **grader/mutator** loop to improve drafts using student agents and rubrics. ([OpenAI Cookbook][4])
- **NotebookLM / Open Notebook** provides the **publishing interface** and AI‑first reading experience; our final content appears as a navigable notebook with sources. ([GitHub][5])
- **Mathematical exploration (AlphaEvolve)** motivates our **iterate‑evaluate‑mutate** template and strict **automated evaluation** mindset—even though our domain is pedagogy rather than proofs. ([arXiv][7])

---

## 11) Deliverables (docs & ops)

- `/docs/PRD_PoC.md` (this document distilled), `/docs/ARCHITECTURE.md` (sequence diagrams; WM schema), `/docs/AGENT_ROLES.md`, `/docs/TOOLS.md` (CodeAct tool catalog).
- `/scripts/run_poc.py` (or `make poc`) to run the pipeline.
- `/ui/README.md` with how to view trace and open the exported **Open Notebook** notebook.

---

## 12) Verification & Ablations

- **Baseline**: teacher only (no sub‑agents), no world model — capture output quality + student score.
- **+World model** only — show better grounding/citations.
- **+Students** — show improvement in coverage/clarity and pass rate.
- **+Recursion** — show faster convergence or better structure vs. flat orchestration.

---

### Key external references you’ll use while implementing

- **RLM concept & minimal implementation** — blog + repo (classes: `RLM_REPL`, sub‑LM calls; depth‑1). ([Alex L. Zhang][1])
- **DSPy CodeAct** — constructor, restrictions (pure tools, no imports), and iteration behavior. ([dspy.ai][2])
- **Open Notebook** — repo structure for API/backend + frontend. ([GitHub][5])
- **Self‑Evolving Agents** (grader/mutator loop template). ([OpenAI Cookbook][4])
- **Kosmos world model** (shared state across agents + citations discipline). ([arXiv][3])
- **AlphaEvolve (Math exploration)** (iterate→evaluate→mutate mindset). ([arXiv][7])

---

## 13) Next Actions (very concrete)

1. Create `schema.sql`, `ingest_handcrafted.py`; commit `/data/handcrafted/database_systems/*`.
2. Implement **3 CodeAct tools** first: `get_concepts`, `run_sql`, `on_add_section`; smoke test CodeAct calls. ([dspy.ai][2])
3. Wrap **RLM_REPL** with `use_codeact` exposed; run a toy teacher→TA sequence that writes a claim to the world model. ([GitHub][6])
4. Add **Student‑QA** and a single **mutation** operator; verify the loop modifies the section and improves score (log provenance).
5. Add **Open Notebook export** endpoint to your fork if needed and wire in `on_create_notebook`/`on_add_section`. ([GitHub][5])
6. Add simple **UI** for trace and a link to the rendered notebook.

---

[1]: https://alexzhang13.github.io/blog/2025/rlm/ "Recursive Language Models | Alex L. Zhang"
[2]: https://dspy.ai/api/modules/CodeAct/ "CodeAct - DSPy"
[3]: https://arxiv.org/abs/2511.02824?utm_source=chatgpt.com "Kosmos: An AI Scientist for Autonomous Discovery"
[4]: https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining?utm_source=chatgpt.com "Self-Evolving Agents - A Cookbook for Autonomous ..."
[5]: https://github.com/lfnovo/open-notebook "GitHub - lfnovo/open-notebook: An Open Source implementation of Notebook LM with more flexibility and features"
[6]: https://github.com/alexzhang13/rlm "GitHub - alexzhang13/rlm: Super basic implementation (gist-like) of RLMs with REPL environments."
[7]: https://arxiv.org/abs/2511.02864?utm_source=chatgpt.com "Mathematical exploration and discovery at scale"
[8]: https://nsuworks.nova.edu/cgi/viewcontent.cgi?article=1130&context=fdla-journal&utm_source=chatgpt.com "NotebookLM: Revolutionizing Learning for Students with ..."
