# Plan – ccopilot-lsk (Student grader keyword matching should respect word boundaries)

## Goal
The student grader’s `_default_keyword_check` currently uses naive substring checks, so keywords like "sql" flag inside "nosql" and "goals". This causes false positives in grounding/pedagogy checklists. Update the matcher to respect word boundaries (using regex) and add regression coverage proving we no longer match partial words.

## Steps
1. Update `_default_keyword_check` in `apps/orchestrator/students.py` to use word-boundary-aware regex matching (and return the exact token hit as evidence).
2. Add unit tests in `tests/test_students.py` (or a new focused test) covering tokens like `sql` vs `nosql` and verifying true hits when full words exist.
3. Run `pytest tests/test_students.py -q`.
4. Update plan + notify via Agent Mail.

## Progress
- 2025-11-13 01:36Z – Added explicit boundary regression tests in `tests/test_students.py`; existing implementation already respected word boundaries. `pytest tests/test_students.py -q` → 8 passed.
