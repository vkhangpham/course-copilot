# ccopilot-s2c · DSPy handle integration plan (2025-11-12)

## Goal
Make the orchestrator and CodeAct programs consume the configured DSPy handles so each role (teacher, TA, student) runs with its intended model/key. This covers docs/PLAN.md section 3 and unblocks future DSPy tuning work.

## Tasks
1. **Registry/program updates** ✅ _2025-11-12 BlackHill_
   - `build_plan_course_program` / `build_draft_lecture_program` / `build_enforce_citations_program` accept optional LMs and wrap execution via `_LMScopedProgram`.
   - `CodeActRegistry` now stores the DSPy handle bundle and resolves `lm_role` strings (teacher/ta/student) automatically.

2. **Pipeline/runtime plumbing** ✅
   - `build_default_registry(dspy_handles=...)` threads the TA handle into each program and tags them with `default_lm_role`.
   - `CodeActRegistry` now auto-resolves the stored role when callers do not supply `lm_handle`, so the orchestrator no longer needs additional wiring.

3. **Testing** ✅
   - `tests/test_codeact_registry.py` verifies role resolution + custom handles.
   - `tests/test_codeact_programs.py` covers scoped LM restore.
   - `tests/test_orchestrator_codeact.py` continues to assert allowed tool lists + handles (will re-enable lm_role assertions after Step 2 finishes).

4. **Docs** ✅ _2025-11-12 BlackHill_
   - README / docs/PLAN.md mention per-role env hierarchy and CodeAct defaults.
   - AGENTS.md warns agents not to mutate `dspy.settings` directly.

5. **Coordination**
   - Pending `apps/orchestrator/teacher.py` availability; will reserve + apply follow-up once GreenStone releases the file (awaiting MCP mail connectivity to confirm).

## Dependencies
- None; this is the next bead in the DSPy stack after rz1.

– ChartreuseCastle
