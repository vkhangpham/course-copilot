# Portal UI + Backend scaffold plan (ccopilot-m6z)

## Goals
- Provide a small FastAPI service that surfaces the artifacts emitted by `coursegen-poc` so the UI (and future operators) can inspect runs without opening files manually.
- Stand up a Next.js + shadcn interface that consumes the new API, highlights recent runs, and links to the generated course plan / lecture artifacts.

## Backend outline (`apps/portal_backend`)
- FastAPI app with CORS enabled for the local Next.js dev server.
- Settings class exposing `outputs_dir` (default `outputs/`).
- Helpers to find the latest run manifest under `outputs/artifacts/run-*-manifest.json` and to hydrate snippets from `course_plan.md`, `lectures/*.md`, and the evaluation report.
- Endpoints:
  - `GET /health` → `{status:"ok", latest_run_id}`
  - `GET /runs` → array of run metadata (id, timestamp, highlights booleans)
  - `GET /runs/{run_id}` → manifest payload + derived summaries
  - `GET /runs/{run_id}/course-plan` & `/lecture` → raw markdown for embedding/download
- Later we can extend with websocket streaming or filters, but above keeps things simple.

## Frontend outline (`frontend/`)
- Next.js 14 app router + TypeScript + Tailwind + shadcn (using `button`, `card`, `badge` primitives to start).
- Environment variable `NEXT_PUBLIC_PORTAL_API_BASE` for API origin (default `http://localhost:8001`).
- Top-level layout w/ radial gradient background, nav, CTA linking to Open Notebook slug (placeholder until backend wires it).
- Landing page sections:
  1. Run summary cards (overall score, graders, recursion/world model toggles).
  2. World model highlights (concepts/timeline) pulled from `world_model_highlights` in manifest.
  3. Student rubric results list (pass/fail badges).
  4. Notebook link + “open in Open Notebook” CTA.
- Components folder `components/ui/` with shadcn button + card wrappers so future work can expand the design system.

## Dev workflow
- Backend: `uvicorn apps.portal_backend.main:app --reload --port 8001`
- Frontend: `cd frontend && pnpm install && pnpm dev` (choose pnpm for smaller lockfiles; npm/yarn also work if preferred).
- Document everything in README.

## Next steps after scaffold
- Hook backend endpoints to real orchestrator provenance once DSPy wiring lands.
- Add auth & streaming later if needed.
- Flesh out FE pages (run detail view, per-module breakdown, evaluation history).

## 2025-11-12 @ LilacStone progress
- 23:15 UTC – Extended FastAPI `/runs/{run_id}` response (`RunDetail`) to include the orchestrator’s `notebook_export_summary`, updated `tests/test_portal_backend.py` to assert the field, and refreshed the shadcn dashboard with a Notebook exports card that visualizes success/skipped/error counts, note IDs, queued paths, and preflight status badges. Frontend types under `frontend/lib/api.ts` were updated accordingly.
- 23:32 UTC – Added `notebook_export_summary` to the `/runs` list response + `RunHistory` UI so operators can see per-run Notebook health (success/total badge) without opening each manifest. Portal backend + frontend types/tests updated to reflect the new field.
- Next – Expose evaluation attempt summaries via the backend and render them as a timeline card so student-loop iterations are visible without manually inspecting manifests.
- 23:48 UTC – Parsed evaluation attempts from the manifest, exposed them via `RunDetail`/`/runs/latest`, updated tests, and added a “Evaluation attempts” card in the shadcn dashboard so student-loop mutations (scores, quiz pass rates, failing rubrics) are visible at a glance.
