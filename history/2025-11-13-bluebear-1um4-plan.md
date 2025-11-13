# Plan: Deep audit of scientific stack (ccopilot-1um4)

## Objectives
- Review recent scientific stack additions (orchestrator, CodeAct tools, world model adapters) for correctness, reliability, and security risks.
- Identify concrete defects or high-risk gaps, capture them in beads, and fix the most critical issues directly when feasible.
- Keep other agents aligned via Agent Mail, bead updates, and inline plan notes.

## Approach
1. **Scope & Signals**: map out relevant modules (world_model/, apps/orchestrator/, apps/codeact/tools/, tests/) and read recent diffs.
2. **Static Review**: inspect code for logic errors (state handling, data races, missing validation, insecure defaults) and misleading docs/tests.
3. **Dynamic Validation**: run focused pytest targets covering belief network + world model tools; extend tests when gaps appear.
4. **Fix / Document**: patch any confirmed issues (include regression tests). If fix is large/out-of-scope, open follow-up beads.
5. **Communication**: announce work start + major findings via Agent Mail thread `bd-ccopilot-1um4`; log updates in this file.

## Current Status
- 2025-11-13 09:47 PT – Initialized bead, registered as BlueBear, preparing deep dive into world model + orchestrator.
- 2025-11-13 09:48 PT – Reserved orchestrator/codeact/world_model/tests paths and notified GreenCreek via Agent Mail thread `[ccopilot-1um4]`.
- 2025-11-13 10:02 PT – Audit uncovered that `ScientificEvaluator._extract_citations` ignores compact citations like `[Codd1970]`, zeroing citation metrics; plan to fix extraction + add regression tests.
- 2025-11-13 10:10 PT – Refactored citation extraction to tokenize generic bracket/parenthetical references, added regression test for `[AuthorYear]` citations, and ran `pytest tests/test_scientific_evaluator.py` (pass).
- 2025-11-13 10:25 PT – Implemented real module parsing + prerequisite detection in `ScientificEvaluator`, added satisfaction tests, and re-ran `pytest tests/test_scientific_evaluator.py` (pass).
- 2025-11-13 10:37 PT – Extended citation extraction to split comma-delimited tokens and capture bare DOI/URL references; added regression tests for DOI/url + multi-citation blocks and re-ran `pytest tests/test_scientific_evaluator.py` (pass).
- 2025-11-13 10:48 PT – Fixed `estimate_cognitive_load` sentence splitting (regex + blank filtering) and added `test_cognitive_load_handles_clean_sentence_splits`; `pytest tests/test_scientific_evaluator.py` remains green.
- 2025-11-13 11:05 PT – Overhauled spaced-repetition heuristics (concept normalization + keyword fallback + graded gap scoring) and added unit tests for even vs sparse spacing; suite passes (`pytest tests/test_scientific_evaluator.py`).
- 2025-11-13 11:12 PT – Reviewed inbox (coord with BlackMountain + FuchsiaMountain) and queued next audit slice: difficulty progression heuristics.
- 2025-11-13 11:20 PT – Capped cognitive-load factors to [0,1], added density stress test, `pytest tests/test_scientific_evaluator.py` now runs 12 cases (pass).
- 2025-11-13 11:32 PT – Reworked difficulty progression scoring (normalized lecture difficulty + gradient penalties) and expanded regression suite (`pytest tests/test_scientific_evaluator.py`, 16 cases).
- 2025-11-13 11:38 PT – Fixed missing import in `apps/orchestrator/student_loop.py` (StudentQuizEvaluator type hints were unresolved) and re-ran `pytest tests/test_students.py` (pass).
