# Plan – ccopilot-nqmn (Quiz evaluator should keep short domain acronyms)

## Goal
Ensure StudentQuizEvaluator doesn’t drop short-but-critical acronyms (SQL, OLTP, ACID) when deriving keyword heuristics so those quiz questions can actually pass when lectures mention them.

## Steps
1. Document how the current 4+ character filter leaves some quiz entries with zero keywords, making success impossible.
2. Update `QuizQuestion.keywords` to fallback to 3+ character tokens when the primary filter empties, keeping domain acronyms intact without reintroducing one-letter noise.
3. Add a regression test demonstrating that a lecture mentioning “SQL” satisfies a quiz whose answer sketch is just “SQL”.

## Progress
- 2025-11-13 04:51Z – Reproduced the issue: answer sketches containing only “SQL” yield zero keywords, so matched_keywords stays empty regardless of lecture content.
- 2025-11-13 04:54Z – Implemented fallback tokenization in `apps/orchestrator/student_qa.py` (>=4 first, drop to >=3 if empty) and added `tests/test_students.py::test_student_quiz_evaluator_handles_short_acronyms`. `pytest tests/test_students.py -q` passes (13 tests).
