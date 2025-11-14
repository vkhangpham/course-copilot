# CourseGen PoC Demo Runbook (bd ccopilot-d1p5.6)

This guide captures the exact steps we expect reviewers to follow for the Database Systems PoC demo: hydrate the handcrafted world model, run the orchestrator CLI (online or offline teacher), confirm the emitted artifacts, and surface the results in the portal dashboard. Treat it as the canonical script for live walkthroughs and CI-style smoke tests.

## 0. Prerequisites & environment checklist

| Area | Details |
| --- | --- |
| Python | 3.11.x virtualenv. Install the repo in editable mode: `pip install -e .` (or `uv pip install -e .`). |
| Node / Deno | Node 18+ (for the Next.js portal) and Deno (for DSPy CodeAct tooling). Install FE deps via `pnpm install` (or `npm install`) inside `frontend/`. |
| Submodules | `git submodule update --init --recursive` (pulls in `vendor/rlm` + `vendor/open-notebook`). |
| Secrets | `.env` already stores real keys—**do not edit/commit it**. Export the following in your shell or `.env.local`:
- Teacher RLM + CodeAct: `OPENAI_API_KEY_TEACHER`, `OPENAI_API_KEY_TA`, `OPENAI_API_KEY_CODER`, `OPENAI_API_KEY_STUDENT` (falls back to `OPENAI_API_KEY`).
- Notebook: `OPEN_NOTEBOOK_API_BASE`, `OPEN_NOTEBOOK_API_KEY`, `OPEN_NOTEBOOK_SLUG`, optional `OPEN_NOTEBOOK_EXPORT_DIR`, `OPEN_NOTEBOOK_AUTO_CREATE`, `OPEN_NOTEBOOK_EXPORT_MIRROR`.
- Portal UI: `NEXT_PUBLIC_PORTAL_API_BASE` (defaults to `http://localhost:8001`), `NEXT_PUBLIC_NOTEBOOK_BASE`, `NEXT_PUBLIC_TRIGGER_RUN_URL` (optional).
| Misc | If you want to point the teacher at a different checkout, set `COURSEGEN_VENDOR_RLM_PATH=/abs/path/to/rlm`. Leave unset to use `vendor/rlm`.

_Tip:_ If you only have a single `OPENAI_API_KEY` in `.env`, every role will automatically fall back to it. The per-role env vars are purely optional overrides.

### Optional offline overrides
- `--offline-teacher` flag (or `COURSEGEN_RLM_OFFLINE=1`) keeps the teacher loop deterministic without hitting the vendor RLM.
- `COURSEGEN_CODEACT_OFFLINE=1` forces the TA CodeAct programs into scaffolding mode (useful when API keys are not available, but course artifacts will be placeholder text).
- `COURSEGEN_DISABLE_LLM_STUDENTS=1` fallback for heuristic student graders if you intentionally want to skip the LLM handles.

## 1. Hydrate the handcrafted world model
Run this once per repo refresh or whenever `data/handcrafted/database_systems` changes. **Never** source inputs from
`docs/samples/` or any pre-authored plan/lecture markdown—the demo must derive everything from the handcrafted YAML/CSV
world model plus `config/course_config.yaml` constraints. The bundled `quiz_bank.json` / `course_outline.yaml` act as
world-model reference artifacts only; the runtime pipeline still needs to generate quizzes/outlines on the fly.

```bash
python scripts/ingest_handcrafted.py \
  data/handcrafted/database_systems \
  outputs/world_model/state.sqlite \
  --jsonl outputs/world_model/snapshot.jsonl
```

The script now prepends the repo root to `sys.path`, so it works out-of-the-box (no custom `PYTHONPATH`). Expect the logger to report counts for authors, papers, concepts, timeline rows, etc., and a snapshot JSONL under `outputs/world_model/`.

## 2. Run the orchestrator CLI
Use the minimalist shim unless you need advanced flags:

```bash
python apps/orchestrator/run_poc.py \
  --repo-root . \
  --constraints config/course_config.yaml \
  --concepts data/handcrafted/database_systems \
  --notebook database-systems-poc
```

Additions:
- `--ablations no_world_model,no_students,no_recursion` (comma-separated) to disable subsystems for ablation demos.
- `--offline-teacher` to force deterministic behaviour (flag sets `COURSEGEN_RLM_OFFLINE=1`).
- Hidden `--repo-root` keeps all relative paths anchored; you can invoke the shim from any working directory.

For the canonical CLI (full surface including `--dry-run`, `--ingest-world-model`, etc.) run:

```bash
coursegen-poc --config config/pipeline.yaml --repo-root . --notebook database-systems-poc
```

### Automation shortcut
When you just need to ensure the whole flow works (ingest → CLI → artifact validation), run the helper script:

```bash
# Example offline smoke (skips ingest, disables students for environments without LLM keys)
COURSEGEN_CODEACT_OFFLINE=1 \
COURSEGEN_DISABLE_LLM_STUDENTS=1 \
python scripts/demo_smoke.py \
  --skip-ingest \
  --offline-teacher \
  --ablations no_students \
  --notebook demo-smoke
```

By default the script ingests the handcrafted dataset, launches `apps/orchestrator/run_poc.py`, and ensures that
the manifest, course plan, lecture, highlights, evaluation report, and scientific metrics artifacts exist. Use
`--skip-ingest` when you’ve already built `outputs/world_model/state.sqlite`, and pass `--ablations` / `--offline-teacher`
to mirror the CLI scenarios described above. The script exits non-zero if any step fails or if expected artifacts are
missing, making it suitable for CI smoke jobs.

### Expected CLI hints
A successful run prints:
- `[eval] overall=<score> (rubric=llm, quiz=llm) | rubrics: coverage:PASS(1.000), … | report=outputs/evaluations/run-*.jsonl`
- `[science] blooms=0.912 | coherence=0.887 | citations=0.944 | cite_cov=0.91 | retention=0.72`
- `[highlights] saved to outputs/artifacts/run-*-highlights.json`
- `[notebook] exported <count>/<total> sections -> database-systems-poc (notes: note-123, note-456)` or queued-export hints when offline.

Failures to watch for:
- `student_llm_unavailable` → student handle missing; set `OPENAI_API_KEY_STUDENT` or force heuristics via `COURSEGEN_DISABLE_LLM_STUDENTS=1`.
- `missing_rubrics` / `missing_quiz_bank` → check paths under `evals/` or `data/handcrafted/...`.
- `Notebook export failed` → ensure `OPEN_NOTEBOOK_API_BASE` + `OPEN_NOTEBOOK_API_KEY` or rely on the offline JSONL exporter.

## 3. Verify emitted artifacts
After each run you should see the following under `outputs/` (timestamps omitted):

| Path | Purpose |
| --- | --- |
| `course_plan.md` | Multi-week syllabus emitted by the teacher. |
| `lectures/module_01.md` | Latest lecture/study guide. |
| `evaluations/run-*.jsonl` | Student grader + quiz payload (rubric scores, quiz pass rates, engine metadata). |
| `logs/run-*.jsonl` | Provenance/teacher trace logs. |
| `logs/teacher-trace-*.json` | Teacher RLM trace summary (actions, prompts). |
| `artifacts/run-*-manifest.json` | Canonical manifest: includes ablations, evaluation summary, notebook exports, highlight source, scientific metrics, rubric/quiz engine tags, stage errors. |
| `artifacts/run-*-highlights.json` | Concept/timeline slices plus `highlight_source`. |
| `artifacts/run-*-science.json` | Full scientific evaluator output. |
| `world_model/state.sqlite` | SQLite snapshot referenced by agents/tools. |
| `notebook_exports/*.jsonl` | Offline export queue when `OPEN_NOTEBOOK_API_BASE` is unset or `OPEN_NOTEBOOK_EXPORT_MIRROR=1`.

Key manifest metadata to spot-check:
- `evaluation.overall_score`, `evaluation.rubric_engine`, `evaluation.quiz_engine` – confirms which graders ran (LLM vs heuristic) and their aggregate score.
- `evaluation_engines` in the manifest summary + portal cards – mirrors the CLI `[eval]` hint.
- `teacher_rlm.mode` / `teacher_rlm.reason` – indicates whether the Teacher ran online vs offline.
- `notebook_export_summary` – shows sections pushed/queued plus note IDs surfaced in the portal dashboard.

Quick sanity script:
```bash
jq '.evaluation | {status, overall_score, rubric_engine, quiz_engine}' outputs/artifacts/run-*-manifest.json | head -n 20
```

## 4. Portal dashboard (optional but recommended for demos)

1. **Backend** – expose manifests via FastAPI:
   ```bash
   uvicorn apps.portal_backend.main:app --reload --port 8001
   ```
   - Honors `PORTAL_OUTPUTS_DIR` (defaults to `<repo>/outputs`) and `PORTAL_NOTEBOOK_SLUG`.

2. **Frontend** – Next.js dashboard:
   ```bash
   cd frontend
   pnpm dev  # or npm run dev
   ```
   - Uses `NEXT_PUBLIC_PORTAL_API_BASE` to talk to the backend.

3. Visit `http://localhost:3000` → verify:
   - Run history list shows the latest run with rubric/quiz engine badges (mirrors CLI metadata).
   - Run detail card surfaces overall score, badges for LLM vs heuristic graders, highlight slices, Notebook exports, scientific metrics, trace downloads.
   - Links to teacher trace + scientific metrics JSON work (downloads stay within `outputs/`).

## 5. Optional: standalone student grader smoke
When you only need to re-grade existing lectures:

```bash
python -m apps.orchestrator.eval_loop run \
  --repo-root . \
  --lectures-dir lectures \
  --pattern "module_*.md" \
  --quiet
```

Outputs land in `outputs/evaluations/` with fresh timestamps; useful for testing rubric tweaks without regenerating lectures.

## 6. Notebook verification
- **Default (export-dir) mode.** Leave `OPEN_NOTEBOOK_API_BASE` unset and let bootstrap set `OPEN_NOTEBOOK_EXPORT_DIR=<repo>/outputs/notebook_exports`. Every section push lands in the JSONL queue and the CLI `[notebook]` hint lists the queued paths. This is the configuration `demo_smoke.py` and CI should use.
- **Live API mode.** Point the CLI at the user’s Dockerized instance (e.g., `OPEN_NOTEBOOK_API_BASE=http://localhost:5055`, `OPEN_NOTEBOOK_SLUG=database-systems-poc`, `OPEN_NOTEBOOK_API_KEY=<token>`). Successful pushes surface real note IDs both in the CLI hint and `notebook_export_summary` inside the manifest.
- **Offline inspection.** Even when hitting the API, set `OPEN_NOTEBOOK_EXPORT_MIRROR=1` if you want a JSONL mirror under `outputs/notebook_exports/` for debugging.

## 7. Troubleshooting quick reference

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'ccopilot'` when ingesting | Regenerate using the current script (path handling fixed), or ensure you run from repo root. |
| `Course plan still the old sample` | Delete `outputs/course_plan.md` and rerun CLI; file is `.gitignore`d, so every run should overwrite it. |
| Student graders skipped (`students_disabled`) | Remove `no_students` ablation and confirm `OPENAI_API_KEY_STUDENT` is set (or heuristics explicitly enabled). |
| Notebook export stuck in `queued` | Set `OPEN_NOTEBOOK_API_BASE` & `OPEN_NOTEBOOK_API_KEY` for live runs, or leave base unset to rely on offline JSONL exports. |
| Portal shows no runs | Ensure `apps.portal_backend` points at the same `outputs/` directory that the CLI wrote to (set `PORTAL_OUTPUTS_DIR` if your CLI run happened in another checkout). |

With these steps, a reviewer can ingest the handcrafted dataset, run the orchestrator end-to-end, confirm evaluation metadata (including rubric/quiz engines) via CLI + portal, and point to the exact artifacts produced during the demo. Update this file whenever new CLI flags or required outputs change.
