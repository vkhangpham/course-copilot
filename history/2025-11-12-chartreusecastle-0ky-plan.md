# ccopilot-0ky · Phase C CodeAct tooling plan (2025-11-12)

## Goal
Finish the Phase C checklist so Teacher/TA programs can rely on the DSPy CodeAct sandbox:
1. Complete the DuckDB helper (`apps/codeact/tools_data.py`) so it mirrors the already-functional `apps/codeact/tools/data.py` module and exposes a simple OO wrapper for agents/tests.
2. Expand world-model tool coverage to include the PLAN-mandated mutation endpoints (wm_link, timeline append, outline persistence) and ensure they can be invoked safely from the sandbox.
3. Enforce TA tool whitelists end-to-end so each role can only invoke the tools defined in `TARoleSpec.tool_whitelist`.
4. Add regression tests covering both the data wrapper and the registry whitelist enforcement.

## Work Breakdown
1. **DataTools parity**
   - Reuse the logic inside `apps/codeact/tools/data.py` to implement `DataTools.run_sql()` (read-only guard, dataset registration, DuckDB connection lifecycle).
   - Allow `DataTools` to accept a `dataset_dir` override for tests; default to `data/handcrafted/database_systems`.
   - Cache the DuckDB file under the provided scratch directory to avoid repeated spin-up cost.
   - Update `tests/test_codeact_data.py` to exercise both the functional helper and the class method (already partially wired).

2. **World-model tools**
   - Ensure `apps/codeact/tools/world_model.py` exports `link_concepts`, `append_timeline_event`, and `persist_outline` wrappers pointing to `WorldModelAdapter`.
   - Add adapter helpers if any mutation (e.g., course outline persistence) still lives only in notebooks.
   - Write tests that hit `WorldModelAdapter` against a temporary SQLite file to validate the mutations.

3. **TA tool whitelist enforcement**
   - Extend `CodeActRegistry` (or a small orchestrator helper) so we can request an executable program given a whitelist; the registry should raise if a program would require tools outside the role’s whitelist.
   - Alternatively wrap the program execution so only the intersection of requested tools is passed to `dspy.CodeAct`.
   - Update `agents/ta_roles.py` with final tool names for each role and ensure the orchestrator honors them.
   - Add unit tests for the registry helper that simulate a TA role missing a required tool (expect ValueError) and a happy path where the whitelist matches the registered program.

4. **Documentation & readiness**
   - Update `docs/PLAN.md` / `docs/ARCHITECTURE.md` references if the tool names change.
   - Record the new tests + env expectations in README once code lands.

## Dependencies
- Blocked on `FuchsiaStone` releasing the overlapping reservations on `apps/codeact/registry.py`, `apps/codeact/programs.py`, `apps/codeact/tools_data.py`, `agents/ta_roles.py`, and `tests/test_codeact_registry.py`.
- Once access is granted, tackle items in the order above so downstream beads (`ccopilot-ki7` et al.) can start immediately.

## Open Questions
- Does anyone else rely on the `DataTools` class in long-running processes? Need confirmation before changing its initialization semantics.
- Should we enforce whitelists inside DSPy program construction or at orchestrator call sites? (Leaning toward a thin wrapper around `CodeActRegistry.build_program`.)

– ChartreuseCastle
