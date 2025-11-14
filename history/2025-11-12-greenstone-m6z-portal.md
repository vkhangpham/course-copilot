# ccopilot-m6z updates (2025-11-12 · GreenStone)

## Work completed
- Refactored the portal UI into reusable components:
  - `RunDetailSection` renders the hero/stats/world-model/rubric/ablation/teacher-trace cards plus notebook export + trace download lists.
  - `RunHistory` lists recent runs with score badges and deep links.
- Home page now consumes those components and keeps the gradient hero framing.
- Added `/runs/[runId]` so operators can open any manifest directly; the page reuses the same detail + history components and shows a friendly fallback when the run is missing.
- Surfaced new actions (course plan, lecture, trace downloads) that call the FastAPI endpoints.
- Surfaced notebook export status and section counts inline, matching the ccopilot-5fr/ccopilot-ofe expectations.
- Installed/linted the frontend (`pnpm install && pnpm lint`) and captured the generated pnpm lockfile + ESLint config so CI can run `next lint` without prompts.

## Next steps / open questions
1. Wire backend trace metadata into a `/runs/{id}/notebook-exports` endpoint if we ever need richer provenance than the manifest blob.
2. Add a per-run mutation log or CodeAct trace viewer once ccopilot-syy lands the recursive teacher loop.
3. Evaluate whether we want static build output in `frontend/out/` for packaging alongside the FastAPI app (requires a follow-up bead once backend endpoints stabilize).

### 2025-11-12 23:45 UTC update (GreenStone)
- Implemented the `/runs/{run_id}/notebook-exports` endpoint plus sanitized `NotebookExport` payloads returned with `RunDetail`.
- Added `/runs/latest` so the portal can grab the freshest run detail without guessing the ID; tests cover the new endpoint.
- Updated the portal UI to consume the structured exports and display status/notebook/note IDs directly.
- Front page now calls `/runs/latest` instead of guessing the run ID, and README documents the new endpoints + UI behavior.
- Hardened path resolution so the portal only serves files under `outputs/`; manifests referencing external paths now return 404 instead of leaking arbitrary files. Added tests covering `PortalSettings.resolve_path` + endpoint behavior.
- Surfaced `evaluation_attempts` via the portal API and UI (new card showing quiz pass rates + failing rubrics), so operators can see whether the mutation loop retried before publishing.
- While reviewing adjacent helpers, cleaned up `ensure_notebook_exists` (removed redundant cache-key assignments) and added a regression test proving `push_notebook_section` only calls the auto-create endpoint once per base/slug.
- Linted the frontend after syncing deps. README/doc updates pending because README is still reserved; will add once locks clear.
- Attempted Agent Mail sends + reservation releases multiple times but the service is timing out (see worklog); will resend/release once MCP Agent Mail is responsive again.

File reservations: currently holding `frontend/**` and `apps/portal_backend/**` while testing; will release once reviewers are unblocked or after the next pass.
