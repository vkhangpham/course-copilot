# Plan – ccopilot-lsk (Student grader keyword matching should respect word boundaries)

## Goal
`StudentGraderPool` uses substring checks (``keyword in text``) for rubric enforcement, so keywords like "sql" match "NoSQL" and falsely satisfy coverage requirements. Tighten the heuristics to match whole words/phrases and add regression tests proving that "NoSQL" no longer satisfies the "SQL" rubric item unless "SQL" actually appears.

## Steps
1. Reproduce with a lecture snippet that mentions "relational" and "NoSQL" but never "SQL"; observe the coverage rubric still passes today.
2. Introduce a `_keyword_present` helper that uses word-boundary regex checks and update `_require_all`, `_require_any`, `_require_count`, `_default_keyword_check`, and `_check_required_sources` to call it.
3. Add a unit test (e.g., `test_student_grader_pool_does_not_confuse_sql_with_nosql`) asserting the coverage rubric fails when SQL is missing, plus rerun existing student tests.
4. Run `pytest tests/test_students.py -q`, update this plan, and notify via Agent Mail thread `ccopilot-lsk`.

## Progress
- 2025-11-13 01:30Z – ChartreuseBear filed bead after confirming the current grader treats "NoSQL" as satisfying the SQL coverage requirement.
- 2025-11-13 01:31Z – Reproduced the false positive by evaluating a lecture mentioning “Relational … NoSQL … Spanner” (no plain “sql” token); coverage rubric still passed with evidence `sql`.
- 2025-11-13 01:35Z – Added `_keyword_present` word-boundary helper, updated the rubric matchers, introduced `test_student_grader_pool_does_not_confuse_sql_with_nosql`, and ran `pytest tests/test_students.py -q` (7 passed).
