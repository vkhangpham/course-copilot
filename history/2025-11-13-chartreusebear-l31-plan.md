# Plan – ccopilot-l31 (Quiz evaluator keyword detection should respect word boundaries)

## Goal
`StudentQuizEvaluator` uses simple substring membership for keyword hits, so words like "NoSQL" satisfy the SQL aggregation quiz question. Mirror the word-boundary fix we added for the grader: add a helper that enforces word boundaries, update `_keyword_hits`, and add regression tests demonstrating that SQL is only counted when the literal token appears.

## Steps
1. Reproduce by evaluating quiz question `quiz-1` (SQL aggregation) against a lecture containing only the token "NoSQL"; observe a false positive.
2. Introduce a `_keyword_present` helper inside `student_qa.py` (or reuse the grader implementation) and update `_keyword_hits` to rely on it.
3. Add a test in `tests/test_students.py` (or a new quiz evaluator test file) that asserts a NoSQL-only lecture fails the SQL quiz question while a real SQL mention passes.
4. Run `pytest tests/test_students.py -k quiz -q` and then the full module, update this plan, and send a quick note via Agent Mail thread `ccopilot-l31`.

## Progress
- 2025-11-13 01:36Z – ChartreuseBear opened bead after noticing the quiz evaluator still treats “NoSQL” as satisfying SQL prompts.
- 2025-11-13 01:38Z – Added `_keyword_present` to `student_qa` + new `tests/test_student_qa.py::test_quiz_evaluator_respects_word_boundaries`; `pytest tests/test_student_qa.py -q` and `pytest tests/test_students.py -q` now pass.
