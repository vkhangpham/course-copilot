# PRD · Concepedia Course‑Gen PoC (RLM + DSPy CodeAct) — _Domain: Database Systems_ (v0.9)

## 1) Goal & Non‑Goals

- **Goal.** Build a working PoC where a **Teacher LLM** (RLM-style) spawns **TA sub‑agents**, all collaborating in a **shared world model** and executing in a **CodeAct (DSPy) sandbox**, to produce:
  1. a **course plan** and 2) **lecture/study‑guide materials** for _Database Systems_.

- **Non‑Goals.** Multi‑tenant UX, grading at scale, new LLM training; full “production” reliability. We focus on one concept (“Database Systems”) with **hand‑engineered inputs**.

## 2) Why this approach (short)

- **RLM** gives recursive, spawnable agents and structured self‑delegation.
- **CodeAct (DSPy)** supplies a safe, programmable **sandbox with tools** for code execution, retrieval, and data wrangling—so agents _think with code_ rather than only chatting.
- **NotebookLM‑style “Open Notebook”** is used at the **final content assembly** step (grounded writing, citations, transformations). When developing locally, you can point `push_notebook_section` at a tiny FastAPI mock + httpx transport (see `tests/test_open_notebook_tools.py`) or run purely offline by setting `OPEN_NOTEBOOK_EXPORT_DIR` to capture JSONL exports (add `OPEN_NOTEBOOK_EXPORT_MIRROR=1` to mirror API pushes to disk).
- **Self‑Evolving Agents** pattern gives a **grader/mutator loop** (“students” as judges) to continually tighten prompts/policies and track versions/rollbacks.

## 3) Inputs → Outputs

- **Inputs (hand‑engineered for this PoC):**
  - _Concept world data_ (**YAML/JSON files**) — taxonomy, key papers & excerpts, seminal authors, subfields, dependency graph, timeline, canonical definitions.
  - _Course constraints_ (**YAML**) — level, focus, learner preferences, prior knowledge, sources to respect/avoid.
  - _Tool configs_ — API keys, dataset paths, Open Notebook REST endpoint.

- **Outputs:**
  1. `course_plan.md` (weeks/modules, outcomes, readings, projects)
  2. `lectures/…` (weekly study‑guides with explanations, examples, exercises, citations), optionally pushed to Open Notebook as sources/notes.

---

# System Overview

**Agents & State.**

- **Teacher (RLM orchestrator):** plans, spawns TAs, maintains global plan, accepts grading feedback, updates prompt/policy versions.
- **TAs (RLM‑spawned):** focused roles (Syllabus Designer, Reading Curator, Exercise Author, Explainer, Timeline Synthesizer, Assessment Writer).
- **Students (Graders/Mutators):** simulated learners use rubrics to grade; provide natural‑language rationales for _why_ a lecture or plan passes/fails; drive the **Self‑Evolving** loop.
- **Shared State / World Model:** concept graph + evidence store + artifacts log; every agent reads/writes it.
- **CodeAct (DSPy) Sandbox:** one **system‑level** sandbox offering tools (Python execution, retrieval, OpenAlex/arXiv mining, citation helpers, template renderers). _There is no agent called “TA‑CodeAct”; TAs call CodeAct tools._
- **Open Notebook (NotebookLM‑style):** final shaping, grounding, citations, and transformations; REST API lets us push sources/notes and then generate study‑guides with references.

> **Architecture diagram:** see the interactive FigJam above (Teacher ↔ TAs ↔ Shared State; TA→CodeAct→Tools; Students→Evals→feedback; Notebook as finalizer).

---

# Execution Plan (Step‑by‑Step)

## 0) Repo layout & submodules (assume you’ve already cloned with submodules)

```
concepedia-course-poc/
├─ apps/
│  ├─ orchestrator/           # RLM teacher + TA roles + loop runner
│  ├─ codeact/                # DSPy-based tool sandbox (system-level)
│  └─ ui/                     # thin operator UI (Next.js) + Open Notebook link-outs
├─ data/
│  ├─ concept/                # hand-engineered world data (YAML/JSON)
│  └─ constraints/            # learner/course constraints (YAML)
├─ outputs/                   # generated plans/materials (md/pdf)
├─ vendor/
│  ├─ rlm/                    # submodule (per your fork mapping, see note below)
│  └─ open-notebook/          # submodule (per your fork mapping)
└─ docs/                      # this PRD, API notes, rubrics, runbook
```

**Note:** Per your instruction, submodules are already cloned:

- **RLM implementation** is available under your fork mapping: `https://github.com/vkhangpham/rlm` (RLM)
- **Open Notebook** under `https://github.com/vkhangpham/open-notebook` (Open Notebook)
  Use the local `vendor/rlm` and `vendor/open-notebook` paths as truth when coding.

Run once:

```bash
git submodule update --init --recursive
```

## 1) Environment

- **Python 3.11+**, **Node 18+**.
- Create `.env` in repo root with (examples):

```
OPENAI_API_KEY=...
OPENALEX_BASE=https://api.openalex.org
ARXIV_BASE=https://export.arxiv.org/api
OPEN_NOTEBOOK_API_BASE=http://localhost:5055  # default in their stack
```

- _(Optional)_ Local LLMs via Ollama if desired by CodeAct.
- The teacher REPL is loaded from `vendor/rlm` by default. If you are iterating on a separate checkout, export `COURSEGEN_VENDOR_RLM_PATH=/abs/path/to/rlm` before running the CLI so the orchestrator imports the correct module.

## 2) Stand up **Open Notebook** (NotebookLM‑style)

- Use the provided Docker compose in the submodule (Next.js front‑end; FastAPI back‑end; SurrealDB).
- Confirm REST access:
  - `POST /api/notebooks` → create notebook `database-systems-poc`
  - `POST /api/sources` → add sources (PDFs, URLs, excerpts)
  - `POST /api/notes` → add AI/Human notes, run transformations (summaries, outlines)
  - These features—multi‑format sources, recursive summarization, grounded Q&A, REST API—are core to Open Notebook’s design.

## 3) Build **Shared State / World Model** (files + simple store)

- **Data model (YAML examples).**
  - `data/concept/taxonomy.yaml` — canonical topics → subtopics
  - `data/concept/papers.yaml` — key papers with fields: `id, title, authors[], venue, year, url, key_points[], canonical_excerpt`
  - `data/concept/graph.yaml` — edges `source -> target` with relation types (pre‑req, influences, is‑part‑of)
  - `data/concept/timeline.yaml` — events with `year, what, why-it-matters`
  - `data/concept/definitions.yaml` — canonical terms + short/long definitions + citations

- **Evidence store.** Keep normalized JSON lines under `data/concept/snippets.jsonl` with `paper_id, span, citation, tags`.
- **Artifacts log** at `shared_state.sqlite` or `shared_state.jsonl` (append by agents) with `{agent, role, step, inputs_hash, output_uri, time}`.
- **Minimal Python access layer** in `apps/orchestrator/shared_state.py` to read/write these.

## 4) Implement **CodeAct (DSPy) Sandbox**

- **One system‑level toolbox** exposed to agents via function calling; implement as a DSPy program with typed signatures (examples):

```python
# apps/codeact/tools.py
class PyExec(dspy.Signature):
    """Run Python code in sandbox and return stdout + artifacts path."""
    code: str
    returns: dict

class SearchOpenAlex(dspy.Signature):
    """Search OpenAlex for works/authors; return JSON summaries."""
    query: str
    returns: list

class FetchArxiv(dspy.Signature):
    """Fetch arXiv entry & pdf link by query or id."""
    query: str
    returns: dict

class CiteBibTeX(dspy.Signature):
    """Return BibTeX for a DOI or arXiv id."""
    id: str
    returns: str

class PushToOpenNotebook(dspy.Signature):
    """Create/add notes & sources to Open Notebook via REST."""
    notebook_id: str
    title: str
    content_md: str
    citations: list
    returns: dict
```

- Provide safe execution (timeouts, no OS shell, whitelist modules), and token budgets.
- Export a single **tool registry** (Python object) that TAs receive via RLM tool‑use.

> **Why Open Notebook here?** It acts as a _grounded writing & study workspace_ (sources, notes, chat, transformations, citations) and can be driven via REST—ideal for final course materials.

## 5) Wire **RLM** (Teacher + TAs)

- In `apps/orchestrator/teacher.py`, write a **Teacher** that:
  1. reads _constraints_ & _concept data_,
  2. drafts an initial **syllabus skeleton**,
  3. **spawns** TA roles (RLM style) with bounded mandates & tool access,
  4. coordinates a few **turns** of collaboration via the shared state,
  5. posts drafts to Open Notebook for grounding and transformation,
  6. chunks plan/lecture markdown into notebook-friendly sections (≤5 plan slices, ≤3 lecture slices) and logs export summaries for observability,
  7. triggers **student graders** and absorbs feedback into prompt/policy updates.

- In `apps/orchestrator/ta_roles/…`, define:
  - `syllabus_designer.py` — weekly modules/outcomes
  - `reading_curator.py` — canonical & alternative readings (with _why_)
  - `explainer.py` — concept explainers, worked examples
  - `exercise_author.py` — exercises, projects, rubrics
  - `timeline_synthesizer.py` — historical framing & modern directions

- RLM pattern: Teacher assembles a **call graph** (recursive), each TA gets **shared state handles** and **CodeAct tool‑stubs**; TAs **must** log decisions to `S3: Progress Log`.

## 6) Define **Students (Graders/Mutators)** & the **Self‑Evolving loop**

- Create `docs/rubrics/` with machine‑readable rubrics (JSON) + natural‑language prompts. Examples:
  - Coverage (0–1): _Do lectures hit core DBS topics (modeling, relational algebra, SQL, normalization, transactions/ACID, indexing, query planning, concurrency, logging/recovery, distributed DB, NoSQL, MVCC)?_
  - Depth/Level: matches specified audience?
  - Grounding: every key claim has a citation back to sources?
  - Pedagogy: learning outcomes, examples, exercises are coherent?

- **Automated graders**: combine rule checks + **LLM‑as‑judge**. Track **scores + rationales**; update **prompt versions** on failure; keep rollback. This mirrors the cookbook’s loop (multi‑grader signals, lenient‑pass threshold, versioned prompts, rollback).
- If OpenAI Evals isn’t available, run graders locally (rule‑based + LLM calls) and persist scores to `eval_runs.jsonl`.

## 7) Hand‑engineer the **Database Systems** dataset (starter pack)

Place into `data/concept/…`:

- `taxonomy.yaml` —

  ```
  - Data Modeling:
      - ER modeling
      - Relational model
  - Query Languages:
      - Relational algebra
      - SQL (DDL/DML)
  - Design & Normalization:
      - FDs, Normal Forms
  - Storage & Indexing:
      - B+-trees, Hashing
  - Query Processing:
      - Cost models, join algorithms
  - Transactions:
      - ACID, 2PL, deadlocks, MVCC
  - Recovery:
      - ARIES, logging, checkpoints
  - Concurrency Control:
      - Locking, OCC
  - Distributed & Modern:
      - Replication, sharding, CAP, NoSQL
  ```

- `papers.yaml` — Papadimitriou, Gray & Reuter, Stonebraker, Hellerstein et al., ARIES, Volcano, System R, Calvin, Spanner, etc. Include canonical excerpts for grounding.
- `timeline.yaml` — System R (1970s), Postgres (1980s–90s), ARIES (1992), etc.
- `definitions.yaml` — “transaction,” “serializability,” “log‑structured storage,” with citations.

## 8) Produce **course plan** and **lectures**

- The Teacher orchestrates TA turns → commits **`outputs/course_plan.md`** and a folder of **study‑guides** (`outputs/lectures/W01.md`, …).
- Push final materials into **Open Notebook** so the operator can use its guided tools (learning guide, summarizations, podcast generator, etc.) for review/iteration.
  - Examine the generated `notebook_export_summary` in `outputs/artifacts/run-*-manifest.json` (and CLI `[notebook]` hint) to confirm how many sections landed, which note IDs were created, and whether any exports were skipped/queued.

## 9) Evaluate → Evolve → Iterate

- Run graders; attach rationales; if below threshold, **update prompt/policy** and rerun a limited loop (3 attempts) with **version tracking & rollback** exactly as in the cookbook pattern. Keep an **eval dashboard** in `docs/eval_report.md` with score histories & deltas.

## 10) Operator UI (thin)

- A minimal **Next.js** panel (apps/ui) to:
  - load constraints, pick dataset,
  - run **“Generate Plan”** → “Generate Lectures,”
  - display eval scores & prompt version history,
  - deep‑link into **Open Notebook** notebook for final editing & export.
    _(Open Notebook itself is the heavier UI for grounded content.)_

---

# Implementation Notes (with concrete pointers)

## RLM (Teacher & TAs)

- **Spawn pattern.** Teacher builds a task tree; each TA is a sub‑agent given: role mandate, shared‑state handles, and the **CodeAct tool registry**.
- **Memory/State.** All agents read/write:
  - `shared_state.concept_graph` (taxonomy, relations)
  - `shared_state.evidence` (snippets with citations)
  - `shared_state.artifacts` (links to drafted markdown, notebook IDs)

- **Versioned prompts.** Maintain a `versioned_prompt.json` per role; on eval failure, attach grader rationale and bump version; on success, pin as baseline.

## CodeAct (DSPy)

- Keep **one** sandbox. TAs call it via function‑calling. Block network except whitelisted hosts (OpenAlex, arXiv, Open Notebook API). Limit CPU/time/memory per call.
- Provide **deterministic transforms** (e.g., LaTeX → Markdown, table generation, quiz generator) so graders can assert properties (length, structure, presence of terms).

## Open Notebook (NotebookLM‑style)

- Use **REST** for: create notebook, upload sources (PDF, URLs, excerpts), write notes, run “Transformations” (summaries/outlines), then export to MD/PDF as needed.
- The system’s strengths—**document‑grounded answers, citations, multi‑provider LLM support, transformations**—make it ideal to finalize lecture content.

## Students/Graders loop

- Combine **rules** (e.g., coverage check vs taxonomy, citation presence, length bounds) with **LLM‑as‑judge** rubrics. Keep a “lenient pass” threshold and maintain **rollback** + **aggregate best** selection across attempts, per the cookbook.

---

# Deliverables & Acceptance

**Artifacts**

- `outputs/course_plan.md` — complete 10–12 week plan with outcomes, required/optional readings, assessments.
- `outputs/lectures/W01…W10.md` — each includes: learning goals, short explainers, _worked example(s)_, exercises (w/ rubric), reading links, 2–3 review Qs.
- `docs/`:
  - `rubrics/*.json` (grader configs & prompts)
  - `apis/open_notebook_rest.md` (endpoints used, example payloads)
  - `runbook.md` (how to run end‑to‑end)
  - `eval_report.md` (scores, versions, change log)
  - `world_model_schema.md` (YAML schema for concept data)

**Acceptance criteria**

- A new engineer can:
  1. boot Open Notebook,
  2. run the orchestrator to produce a _plausible_ course plan and ≥6 lecture guides,
  3. see grader scores + version history,
  4. open the notebook and verify citations & transformations,
  5. regenerate 1–2 times with measurable improvement in eval metrics.

**Quality bar**

- Coverage ≥ 0.8, Grounding ≥ 0.85, Pedagogy ≥ 0.75 (rubric‑defined) on the “Database Systems” rubric set; each lecture < 1,800 words with ≥ 3 inline citations to sources uploaded to the notebook.

---

# Operator Runbook (CLI)

1. **Boot Open Notebook**

```bash
cd vendor/open-notebook
docker compose up -d
# Confirm API on http://localhost:5055
```

2. **Seed dataset**

```bash
cp -r docs/samples/database-systems/* data/concept/
cp docs/samples/constraints_undergrad.yaml data/constraints/active.yaml
```

3. **Generate plan & lectures**

```bash
cd apps/orchestrator
python run_poc.py --constraints ../../data/constraints/active.yaml \
                  --concept ../../data/concept \
                  --notebook database-systems-poc
```

4. **Evaluate**

```bash
python eval_loop.py --artifacts ../../outputs/lectures \
                    --rubrics ../../docs/rubrics/dbs.json \
                    --versions ../prompts/
```

5. **Inspect in Open Notebook** (grounded edits, podcast, exports).

---

# UI Scope (thin)

- **/run** page: choose constraints, run generation, tail logs.
- **/evals** page: table of attempts (scores, rationales), _View Prompt Diff_.
- **/open-notebook**: deep‑link to the active notebook ID for content polishing.

---

# Data & Schema (minimum)

**`constraints.yaml`**

```yaml
audience_level: "upper-undergrad"
focus: ["transaction processing", "query optimization"]
prior_knowledge: ["discrete math", "basic programming"]
style: { tone: "explanatory", math: "light" }
sources:
  must_include: ["System R papers", "ARIES"]
  avoid: ["blogposts without citations"]
lengths: { lecture_words_max: 1800 }
```

**`papers.yaml` (excerpt)**

```yaml
- id: "aries-1992"
  title: "ARIES: A Transaction Recovery Method ..."
  authors: ["C. Mohan", "D. Haderle", "B. Lindsay", "H. Pirahesh", "P. Schwarz"]
  venue: "ACM TODS"
  year: 1992
  url: "https://doi.org/..."
  key_points: ["physiological logging", "redo/undo", "checkpointing"]
  canonical_excerpt: "..."
```

---

# Risks & Mitigations

- **Eval proxy drift / overfitting to graders.** Use multiple signals + must‑pass checks; keep **rollback**; occasionally review samples manually.
- **Hallucination / weak grounding.** Force citations via Open Notebook pipeline; reject outputs that lack required citations.
- **Prompt bloat & instability.** Keep **versioned prompts** per role; periodically prune; choose **best‑overall** prompt across a validation set, not the last one.
- **Sandbox safety.** Timeouts; dependency whitelist; no shell.
- **Scope creep.** Single domain (DBS); one learner profile.

---

# Appendix A — Folders & Key Scripts

```
apps/
  orchestrator/
    run_poc.py            # main entry; orchestrates teacher loop
    eval_loop.py          # graders + prompt evolution
    teacher.py            # RLM teacher orchestration
    ta_roles/*.py         # TA modules (syllabus, readings, etc.)
    shared_state.py       # IO utils for YAML/JSONL/SQLite
    prompts/
      teacher.json        # versioned
      ta_syllabus.json    # versioned
      ...
  codeact/
    tools.py              # DSPy signatures
    sandbox.py            # execution controller
  ui/
    pages/*               # thin operator UI
data/
  concept/*               # taxonomy, papers, graph, timeline
  constraints/*           # course constraints
outputs/
  course_plan.md
  lectures/W01.md ...
docs/
  prd.md
  world_model_schema.md
  apis/open_notebook_rest.md
  rubrics/dbs.json
  eval_report.md
vendor/
  rlm/                    # RLM submodule (per your fork mapping)
  open-notebook/         # Open Notebook submodule
```

---

# Appendix B — Open Notebook REST (examples)

- `POST /api/notebooks {name:"database-systems-poc"}` → `{id}`
- `POST /api/sources {notebook_id, type:"pdf|url|text", payload:{...}}`
- `POST /api/notes {notebook_id, title, content_md, citations:[...]}`
- `POST /api/transformations {notebook_id, note_id, kind:"summary|outline|qa"}`
  _(Grounded, document‑based synthesis + citations are core features.)_

---

## References (for the implementer)

- **NotebookLM / Open Notebook** — document‑grounded learning assistant with multi‑format sources, transformations, and REST access; used here for final content assembly & citation integrity.
- **Self‑Evolving Agents (OpenAI Cookbook)** — automated grader loop, LLM‑as‑judge, prompt versioning, rollback & aggregate best selection; we mirror this for “students” grading.
