# Plan – ccopilot-a6m (2025-11-12)

## Context
Audit from `history/2025-11-12-orangeMountain-plan-audit.md` flagged that our ablation toggles (`no_world_model`, `no_students`, `no_recursion`) do not actually gate their respective subsystems. We just picked up **ccopilot-a6m** to harden that behavior while keeping tests in sync.

## Tasks / Status
1. ☑ **Recon** – traced the ablation plumbing in `TeacherOrchestrator` and CLI helpers. Gaps: WM highlight artifacts still emit even when `use_world_model` is false; notebook exports run regardless of recursion/world-model flags; provenance/manifest never record that subsystems were skipped.
2. ☑ **Implementation** – hardened `TeacherOrchestrator` so WM highlights/teacher loop/notebook exports all respect the relevant ablations (skip highlight artifact + teacher loop when disabled, gate notebook exports on recursion, short-circuit CodeAct helpers).
3. ☑ **Tests** – added pipeline regression tests for `no_world_model` and `no_recursion` plus a unit test covering clients without `ensure_notebook()`. (Pytests not run locally yet.)
4. ☐ **Docs & comms** – update README/PLAN ablation blurb if behavior changes, close the bead in bd, and send Agent Mail summary once merged.

Will update this file inline as each step completes.
