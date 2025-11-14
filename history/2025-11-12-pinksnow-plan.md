# PinkSnow – Daily Plan (2025-11-12)

## Completed
- **ccopilot-4hm** – Sample course constraints now align with `CourseConstraints`; regression test added; CLI dry-run validated.
- **ccopilot-29t** – `COURSEGEN_VENDOR_RLM_PATH` callout added to PLAN §1.
- **ccopilot-20w** – PLAN Phase A and related sections now reference `vendor/` paths.

## In Progress
- **ccopilot-abu – Track orchestrator student/notebook helpers**
  1. Verify `apps/orchestrator/{student_loop,student_qa,notebook_publisher}.py` + `data/quiz.json` match the versions currently exercised by tests. ✅
  2. Update `apps/orchestrator/__init__.py` exports (if needed) and ensure the new modules/data stay tracked. ✅
  3. Run `pytest tests/test_students.py tests/test_portal_backend.py -q`. ✅
  4. Notify via agent mail + close the bead. ✅

- **ccopilot-25m – Ensure student mutation loop respects per-rubric failures**
  1. Update `_should_continue` so rubric pass only counts when every rubric entry passes (not just the aggregate average). ✅
  2. Add regression coverage proving the loop mutates when overall score is high but a rubric still fails. ✅
  3. Run `pytest tests/test_students.py -q`. ✅
  4. Communicate + close bead. ✅

- **ccopilot-dv1 – Repo layout snippet should reflect vendor dirs**
  1. Update the repo layout block in PLAN §1 to list `vendor/rlm` and `vendor/open-notebook` instead of `external/**`. ✅

- **ccopilot-11c – Docs should reference outputs/world_model/state.sqlite**
  1. Sweep README, docs/ARCHITECTURE.md, docs/WORLD_MODEL_TOOLING.md, and scripts README for references to `world_model/state.sqlite` and update them to `outputs/world_model/state.sqlite`. ✅


## Next Up
1. If no further doc fixes surface, pick the next ready bead (or create one) focused on teacher/CodeAct integration gaps called out in the PLAN audit.
2. Keep README + docs consistent with the active directory layout (`vendor/**` vs `external/**`).

---

# BlueCreek – Daily Plan (2025-11-12)

## In Progress
- **ccopilot-g8v – Allow wm-inspect to honor COURSEGEN_REPO_ROOT**  
  1. ✅ Add env fallback in `scripts/query_world_model.py` so the default store path resolves inside the referenced repo even when the script is installed elsewhere.  
  2. ✅ Extend `tests/test_query_world_model.py` to cover the override plus existing behavior.  
  3. ✅ Update docs (README + `docs/WORLD_MODEL_TOOLING.md` + scripts README) to describe the env var and reference the new workflow.  
  4. ✅ Run targeted pytest and communicate results via Agent Mail before closing the bead.
- **ccopilot-4lu – Dataset tools should honor repo/dataset env overrides**  
  1. ✅ Reproduce the failure by running `coursegen-poc` from outside the repo root (without `cd`) and document the FileNotFoundError from `load_dataset_asset`/`run_sql_query`.  
  2. ✅ Anchor `apps/codeact/tools/data.py` + `DataTools` to `COURSEGEN_DATASET_DIR`/`COURSEGEN_REPO_ROOT`, exporting those env vars during CLI bootstrap/pipeline initialization.  
  3. ✅ Add regression tests covering the env override + non-repo CWD scenario.  
  4. ✅ Communicate via Agent Mail and close the bead once tests pass.

## Next Up
- Sweep recent orchestrator/world-model tooling commits for regressions or missing validation, file/claim additional beads as needed, and address user-requested deep code review items.

## Newly Opened / In Progress
- **ccopilot-9kr – Notebook exports should follow repo/output dir by default**  
  1. ✅ Documented current behavior: offline exports defaulted to caller CWD, so running outside the repo scattered JSONL files.  
  2. ✅ Updated `ccopilot/pipeline/bootstrap.py` to set `OPEN_NOTEBOOK_EXPORT_DIR=<repo>/outputs/notebook_exports` (and ensured the directory exists) whenever the env is unset.  
  3. ✅ Taught `apps/codeact/tools/open_notebook.py` to fall back to `COURSEGEN_REPO_ROOT/outputs/notebook_exports` when the env remains unset.  
  4. ✅ Added regression tests (`tests/test_cli_run_poc.py::test_cli_offline_exports_follow_repo_outputs`) covering offline export paths when invoking the CLI from a non-repo directory.  
  5. ✅ Communicated via Agent Mail + ran targeted pytest suites; ready to close once reviewed.
- **ccopilot-4u1 – Add tests for validate-handcrafted CLI**  
  1. ✅ Captured current CLI behavior (success path already covered; reproduced warnings/errors using minimal fixtures).  
  2. ✅ Added regression coverage (`tests/test_validate_handcrafted_cli_errors.py`) that seeds tiny datasets via CliRunner to assert error handling and warning messages, complementing the existing success + fail-on-warning tests.  
  3. ✅ Verified the tests stay fast (`pytest tests/test_validate_handcrafted_cli.py tests/test_validate_handcrafted_cli_errors.py -q`).  
  4. ✅ Communicated via Agent Mail + closed the bead with GreenBear looped in.
- **ccopilot-xac – Pipeline should load .env from repo_root**  
  1. ✅ Reproduced the failure by running `coursegen-poc` from a temp dir (repo `.env` was ignored).  
  2. ✅ Updated `bootstrap_pipeline` to call `load_dotenv(repo_root / ".env")` and documented the behavior.  
  3. ✅ Added regression coverage (`tests/test_cli_run_poc.py::test_cli_loads_dotenv_from_repo_root_when_running_outside`).  
  4. ✅ Communicated via Agent Mail + closed the bead after tests passed.
- **ccopilot-wzy – TA roles should anchor dataset paths to repo root**  
  1. ✅ Reproduced the failure: instantiating `ExerciseAuthor` from a temp CWD raised FileNotFoundError.  
  2. ✅ Added `apps/orchestrator/ta_roles/dataset_paths.py` and updated `ExerciseAuthor` + `Explainer` to call `resolve_dataset_root`, which honors `COURSEGEN_DATASET_DIR`/`COURSEGEN_REPO_ROOT`.  
  3. ✅ Added regression coverage (`tests/test_ta_roles_paths.py`) that instantiates both roles from a non-repo working directory and confirms they load the dataset via env overrides.  
  4. ✅ Communicated results via Agent Mail + closed the bead after review.
- **ccopilot-vbf – eval_loop should default to repo paths**  
  1. ✅ Reproduced by running `python -m apps.orchestrator.eval_loop --quiet` from `/tmp` (with `PYTHONPATH` pointing at the repo).  
  2. ✅ Updated `apps/orchestrator/eval_loop.py` to accept `--repo-root`, resolve defaults via `COURSEGEN_REPO_ROOT`, and seed the env.  
  3. ✅ Added regression coverage (`tests/test_eval_loop_cli.py`).  
  4. ✅ Communicated via Agent Mail + closed the bead after validation.
- **ccopilot-r62 – no_recursion ablation shouldn't skip TA CodeAct programs**  
  1. ✅ Reproduced the issue (`--ablations no_recursion` skipped PlanCourse/DraftLectureSection).  
  2. ✅ Updated `TeacherOrchestrator` so only the Teacher RLM loop respects the recursion ablation.  
  3. ✅ Added regression coverage (`tests/test_orchestrator_codeact.py::test_recursion_ablation_still_runs_codeact`, `tests/test_cli_run_poc.py::test_cli_no_recursion_still_runs_codeact`).  
  4. ✅ Communicated via Agent Mail + closed the bead after validation.
- **ccopilot-4w6 – no_recursion shouldn't disable notebook exports**  
  1. ✅ Reproduced by running `python apps/orchestrator/run_poc.py --ablations no_recursion`; notebook exports were skipped.  
  2. ✅ Updated `TeacherOrchestrator` so notebook publishing depends solely on the notebook config (not the recursion ablation).  
  3. ✅ Added regression coverage (`tests/test_orchestrator_codeact.py::test_recursion_ablation_keeps_notebook_exports_enabled`, `tests/test_cli_run_poc.py::test_cli_no_recursion_still_runs_codeact`).  
  4. ✅ Communicated via Agent Mail + closed the bead after validation.

# PurpleMountain – Daily Plan (2025-11-13)

## Completed
- **ccopilot-vsh – Student loop should record final failing reason when mutations exhausted**  
  1. ✅ Confirmed that `StudentLoopRunner` drops the final `MutationReason` whenever `iteration > max_mutations`, leaving Portal/eval logs without failing rubric/question metadata.  
  2. ✅ Updated `StudentLoopRunner.run` so the final attempt captures the mutation reason even if no further mutation occurs.  
  3. ✅ Added regression coverage in `tests/test_students.py` for the "max_mutations_reached" scenario and ran `pytest tests/test_students.py -q`.  
  4. ✅ Shared results (mail thread `ccopilot-vsh`) and closed the bead.

- **ccopilot-mxe3 – Portal should backfill world_model_store_exists for legacy manifests**  
  1. ✅ Observed that older manifests (and some stub runs) omit `world_model_store_exists`, so the portal API returned `null` despite having enough context (ablations + store paths) to infer the status.  
  2. ✅ Added `_derive_world_model_store_exists` and wired it through the list/detail endpoints so both the RunList summary and sanitized RunDetail manifest now emit the inferred bool.  
  3. ✅ Extended `tests/test_portal_backend.py` with `test_runs_backfill_world_model_store_exists_when_missing` and re-ran `pytest tests/test_portal_backend.py -q` (17 passed).  
  4. ✅ Shared results via Agent Mail thread `ccopilot-mxe3` and closed the bead.

## Completed
- **ccopilot-tfor – Portal should embed inferred highlight_source into manifest payload**  
  1. ✅ After adding highlight-source inference, noticed the sanitized manifest mirror still omitted the derived value, so clients that read `detail.manifest.highlight_source` continued to see blanks.  
  2. ✅ Injected the inferred highlight source into the sanitized manifest before returning the RunDetail payload so both the top-level field and manifest copy stay aligned.  
  3. ✅ Extended `tests/test_portal_backend.py::test_runs_fallback_highlight_source_when_manifest_missing` to assert the manifest copy now carries the inferred value and reran `pytest tests/test_portal_backend.py -q` (16 passed).  
  4. ✅ Shared results via Agent Mail thread `ccopilot-4gcs` and closed the bead.

## Completed
- **ccopilot-4gcs – Portal should infer highlight source when manifests lack metadata**  
  1. ✅ Found that older manifests (and some dataset-only fallbacks) never wrote `highlight_source`, so the portal run list/detail pages rendered no badge even though we could infer provenance.  
  2. ✅ Added `_derive_highlight_source` in `apps/portal_backend/main.py` (list/detail endpoints + trace labels) to derive `world_model` vs `dataset` based on ablations/store flags/highlights when the manifest leaves the field blank.  
  3. ✅ Added regression coverage (`tests/test_portal_backend.py::test_runs_fallback_highlight_source_when_manifest_missing`) and ran `pytest tests/test_portal_backend.py -q`.  
  4. ✅ Shared results via Agent Mail thread `ccopilot-4gcs` and closed the bead.
- **ccopilot-o1g – bootstrap_pipeline should override COURSEGEN_REPO_ROOT when --repo-root is provided**  
  1. ✅ Reproduced the bug: exporting `COURSEGEN_REPO_ROOT=/repo/A` and then running `python apps/orchestrator/run_poc.py --repo-root /repo/B` kept env vars pointed at `/repo/A` because `bootstrap_pipeline` used `setdefault`.  
  2. ✅ Updated `bootstrap_pipeline` to always set `COURSEGEN_REPO_ROOT` to the resolved repo root argument so downstream tooling (wm-inspect, Notebook exports, CodeAct) follows the active checkout.  
  3. ✅ Added regression coverage (`tests/test_pipeline_runtime.py::test_repo_root_overrides_existing_env`) and ran `pytest tests/test_pipeline_runtime.py -q`.  
  4. ✅ Communicated via Agent Mail thread `ccopilot-o1g` and closed the bead.
