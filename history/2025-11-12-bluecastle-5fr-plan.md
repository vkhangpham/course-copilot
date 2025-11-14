# 2025-11-12 BlueCastle — ccopilot-5fr game plan

## Scope & goals
- Deliver PLAN Phase F requirements: (1) orchestrator always emits notebook exports after Phase E, (2) CLI exposes notebook slug + auto-create toggles, (3) integration tests cover API + offline mirrors.
- Coordinate with ccopilot-ofe (GreenStone) so the new `ensure_notebook` helper and CLI flag align with NotebookPublisher behavior.
- Keep artifacts/provenance updated so downstream CLI hints (`[notebook] ...`) reflect real exports and manifest entries show section metadata.

## Current state audit
- `NotebookPublisher` already chunks course plan + lecture modules and calls `apps.codeact.tools.open_notebook.push_notebook_section`, but it lacks:
  - Support for passing through result metadata to manifests (only raw dicts returned today).
  - Awareness of the upcoming auto-create toggle (it currently relies on env `OPEN_NOTEBOOK_AUTO_CREATE`).
- `TeacherOrchestrator` publishes immediately after eval but does not log per-section status in provenance/manifest beyond raw list.
- CLI `--notebook` and `--skip-notebook-create` flags exist but there is no regression test ensuring exports happen end-to-end with the FastAPI mock (current CLI tests stub OpenNotebookClient but don’t assert exports).
- Reservations (ChartreuseCastle/LilacStone) currently cover `apps/orchestrator/notebook_publisher.py`, `apps/orchestrator/run_poc.py`, and relevant tests, so coding must wait until they release or we pair.

## Task breakdown
    1. **Confirm requirements + unblock files**
       - [x] Wait for reservations on notebook publisher/CLI/tests to clear (pinged in threads `ccopilot-ofe` & `ccopilot-5fr`).
       - [x] Once free, reserve the files with reason `ccopilot-5fr` before editing.
    2. **NotebookPublisher enhancements**
       - [x] Accept optional `auto_create` / `client_factory` args so tests can force inline content/ offline behavior (done: inline content support + chunk builder).
       - [x] Surface structured results (status, note_id/export_path, citations) for manifest + CLI summary (no change needed beyond inline sections; existing response piping retained).
    3. **Orchestrator + manifest wiring**
       - [x] Persist notebook export entries into manifest + provenance (include success/error counts).
       - [x] Handle ValueError vs Exception separately (already done) but ensure CLI `PipelineRunArtifacts.notebook_exports` is never `None` when notebook config exists (even if skipped) so CLI hint can explain the skip.
    4. **CLI / pipeline integration**
       - [x] Ensure `--skip-notebook-create` flips both the config flag and the env `OPEN_NOTEBOOK_AUTO_CREATE` (already via bootstrap) and document expected env precedence.
       - [x] Add CLI test that asserts `[notebook] exported ...` message includes note IDs from the mock server; add failure-path test (API disabled -> offline JSONL path).
       - [x] Respect per-publisher auto-create overrides when calling `push_notebook_section` (fix bug where config flag was ignored unless env var was set).
5. **Docs + coordination**
   - [x] Update README / docs/PLAN / docs/PoC with the new chunking + notebook_export_summary details.
   - [ ] Post status + testing notes via Agent Mail once work lands (mail service was intermittently unavailable; resend once stable).

## Blockers / dependencies
- Waiting on ChartreuseCastle + LilacStone to release reservations (files listed above + README, `tests/mocks/notebook_api.py`).
- Need GreenStone’s auto-create helper merged (ccopilot-ofe) to avoid duplicated logic; will sync changes before finalizing CLI tests.

## Test plan (expected additions)
- Unit: `tests/test_notebook_publisher.py` (structured result + auto-create interactions).
- Tooling: `tests/test_open_notebook_tools.py` (ensure mirror + ensure_notebook called when auto-create enabled, and offline export path remains).
- CLI: `tests/test_cli_run_poc.py` (assert `[notebook] exported` summary includes note IDs; ensure `--skip-notebook-create` disables ensure call).

## Next update
- After reservations clear or at 23:30 UTC (next check), whichever comes first. Will escalate via Agent Mail if still blocked.
