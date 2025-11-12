# PLAN/PoC Compliance Audit – 2025-11-12

## Summary
| Pillar (PLAN §4.x) | Status | Notes |
| --- | --- | --- |
| 4.1 World model & data | ✅ Mostly complete | Handcrafted dataset + ingestion scripts exist with tests (`data/handcrafted/database_systems/*`, `scripts/ingest_handcrafted.py`).
| 4.2 CodeAct sandbox | ⚠️ Partial | Tool wrappers + DSPy programs exist, but no orchestration wiring invokes them and there’s no enforcement of tool whitelists per role.
| 4.3 RLM integration | ❌ Not implemented | Teacher RLM + TA orchestrator still stubs; pipeline emits placeholder markdown instead of running recursive agents.
| 4.4 Students & mutation | ⚠️ Partial | Deterministic rubric grader is in place, but no mutation loop or LLM-based QA agents exist yet.
| 4.5 Open Notebook export | ⚠️ Partial | Tool wrapper exists with env guards, yet orchestrator never calls it and there’s no linkage to a real Notebook server.
| 4.6 UI / Observability | ✅ v0 scaffold | FastAPI portal + shadcn Next.js dashboard now surface run metadata, but traces/agent timelines still TODO.

## Detailed findings

### World model & data (PLAN §4.1)
- ✅ Dataset coverage: taxonomy, concepts, timelines, quiz bank, etc. live under `data/handcrafted/database_systems/` with a README describing ingest steps (`data/handcrafted/database_systems/README.md:1-33`).
- ✅ Ingestion pipeline: `scripts/ingest_handcrafted.py` validates referential integrity, hydrates SQLite/JSONL snapshots, and is invoked automatically by `bootstrap_pipeline` when the store is missing (`scripts/ingest_handcrafted.py:1-220`, `ccopilot/pipeline/bootstrap.py:108-160`).
- ✅ Tests: `tests/test_handcrafted_loader.py` / `tests/test_query_world_model.py` cover the loader + inspection CLIs.
- 🔍 Action: keep datasets aligned with future schema evolutions but no immediate gap.

### CodeAct sandbox (PLAN §4.2)
- ✅ Tool modules exist for WM CRUD, DuckDB SQL, citations, and notebook export (`apps/codeact/tools/world_model.py`, `apps/codeact/tools/data.py`, `apps/codeact/tools/open_notebook.py`).
- ✅ DSPy programs are declared for PlanCourse, DraftLectureSection, and EnforceCitations (`apps/codeact/programs.py:1-60`).
- ⚠️ Missing orchestration: no code currently instantiates these programs during a run. The orchestrator stub never calls `build_plan_course_program` et al., nor does `agents/teacher_rlm.py` expose `use_codeact`/`spawn_ta` required by PLAN §4.3.
- ⚠️ Tool whitelists exist only as static metadata in `agents/ta_roles.py:7-36`, but there is no enforcement layer to ensure each TA’s CodeAct run honors the whitelist.
- ▶ Recommended beads:
  1. Wire `ccopilot.pipeline.runtime` to instantiate `TeacherOrchestrator` that actually invokes the CodeAct programs with the DSPy handles from `PipelineContext`.
  2. Add a TA execution harness that maps `TARoleSpec.tool_whitelist` to `dspy.CodeAct` tool configs (audit stub in `agents/ta_roles.py`).

### RLM + teacher loop (PLAN §4.3, PoC §2)
- ❌ `agents/teacher_rlm.py` only logs placeholder bootstrap + run output and returns `{"status": "not_implemented"}` (`agents/teacher_rlm.py:1-33`).
- ❌ `apps/orchestrator/teacher.py` raises `NotImplementedError` inside `run_coursegen`, so the CLI cannot exercise the intended recursive flow (`apps/orchestrator/teacher.py:28-55`).
- ❌ The runtime currently calls `apps.orchestrator.pipeline.Orchestrator`, which emits static markdown seeded from the dataset rather than invoking TAs or the RLM (`apps/orchestrator/pipeline.py:35-120`).
- ▶ Recommended beads:
  1. Implement `TeacherOrchestrator` to consume prompts/constraints, invoke `TeacherRLM`, and manage the TA subcalls outlined in PLAN §5.
  2. Replace the placeholder orchestrator inside `ccopilot/pipeline/runtime.py` with the real RLM-driven loop once ready, keeping the stub only behind a `--dry-run` flag.

### Students & mutation (PLAN §4.4)
- ✅ Heuristic grader exists (`apps/orchestrator/students.py:1-180`) and is already used when the stub pipeline writes evaluation files (`apps/orchestrator/pipeline.py:115-150`).
- ❌ There’s no student QA agent that generates answers against `quiz_bank.json`, nor a mutation loop that retries drafts when scores fall below thresholds (PLAN §4.4 calls for max two passes).
- ❌ Rubric configuration currently supports keyword heuristics only; there’s no integration with DSPy/OpenAI graders.
- ▶ Recommended beads:
  1. Implement a `StudentQA` CodeAct/DSPy program that samples answers and compares them to quiz bank entries, feeding results back to the main loop.
  2. Add a mutation policy module that reacts to failing rubrics and re-invokes TA roles with updated instructions before publishing.

### Open Notebook export (PLAN §4.5)
- ✅ Tool wrapper now enforces API base presence or offline export opt-in (see `apps/codeact/tools/open_notebook.py:16-80`), and README documents the `OPEN_NOTEBOOK_EXPORT_DIR` fallback.
- ❌ No orchestrator code calls `push_notebook_section`, so nothing is published to Notebook even when API keys are available. The manifest only records placeholder file paths (`apps/orchestrator/pipeline.py:141-200`).
- ❌ No automation exists for creating notebooks or uploading sources; PLAN §4.5 expects at least a thin POST wrapper in our Open Notebook fork.
- ▶ Recommended beads:
  1. Implement a `NotebookPublisher` utility that reads the generated plan/lecture markdown, chunks it, and calls `push_notebook_section` per module.
  2. Provide integration tests that exercise the HTTP path using a mocked Open Notebook API (similar to `tests/test_open_notebook_client.py`).

### DSPy/OpenAI runtime
- ✅ `configure_dspy_models` provisions OpenAI-backed DSPy LMs and is invoked during bootstrap, logging the chosen models (`ccopilot/core/dspy_runtime.py:1-78`, `ccopilot/pipeline/bootstrap.py:56-140`).
- ⚠️ The handles stored on `PipelineContext` are unused because the orchestrator never routes prompts through DSPy programs. We need a handoff layer that maps `ctx.dspy_handles` + CodeAct programs to TA executions.
- ❌ There’s no unit/integration coverage for how DSPy programs respond when the API key is missing or when ablations disable recursion/students.

### UI / observability (PLAN §4.6)
- ✅ The new FastAPI backend (`apps/portal_backend/main.py:1-200`) and Next.js + shadcn frontend (`frontend/app/page.tsx:1-160`) deliver the minimal dashboard requested (world-model highlights, student scores, Notebook link).
- ⚠️ Agent trace visibility is still missing: no endpoint surfaces CodeAct transcripts or RLM provenance (Plan §4.6 bullet 2). Logs exist in `outputs/logs`, but the portal does not expose them yet.
- ⚠️ There’s no button yet to open stored provenance files or run comparisons between runs.
- ▶ Recommended beads:
  1. Extend the portal backend with endpoints for provenance/trace records and expose them visually (timeline or table) in the UI.
  2. Surface ablation toggles and run-state badges so operators can quickly see which subsystems were disabled.

### Ablations & CLI toggles
- ✅ CLI accepts `--ablations` and the config parser maps them to `AblationConfig` (`ccopilot/core/ablation.py:7-50`, `ccopilot/cli/run_poc.py:28-60`).
- ⚠️ Enforcement is limited: orchestrator just logs the values (`apps/orchestrator/pipeline.py:80-120`). When `no_students` is set, we still call `StudentGraderPool` instead of skipping; when `no_world_model` is set, CodeAct tools still query the SQLite store.
- ▶ Recommended beads: add ablation-aware guards (e.g., bypass `_collect_world_model_highlights` and notebook export when disabled) and include tests for each switch.

## Suggested next beads
1. **Implement Teacher RLM loop** – Replace placeholder orchestrator with an RLM-driven pipeline that invokes CodeAct programs and student graders end-to-end.
2. **Notebook publisher integration** – Wire the generated artifacts into `push_notebook_section`, add config for Notebook IDs, and verify through tests.
3. **Student QA + mutation loop** – Introduce DSPy-based QA graders + mutation policies so failing rubrics trigger automated revisions.
4. **Portal trace view** – Extend the new portal to surface provenance/agent traces and ablation indicators so it meets PLAN §4.6 trace requirements.

Let me know if you’d like deeper dives on any specific subsystem; happy to spin out detailed tickets per finding.
