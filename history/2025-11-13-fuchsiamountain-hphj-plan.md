# Plan – ccopilot-hphj (ExerciseAuthor summaries should be case-insensitive)

## Goal
`ExerciseAuthor._concept_summary_map` lowercases concept IDs when building the lookup, but `draft()` later calls `concept_summaries.get(tag, ...)` with the raw `learning_objectives`. If a quiz entry references `ACIDConcept` (mixed case) and the concept file uses the same casing, the lookup misses and we fall back to "Reinforce core concepts" even though a summary exists. Make the lookup case-insensitive so exercises stay grounded regardless of casing.

## Steps
1. Reproduce with a minimal dataset where `concepts.yaml` defines `ACIDConcept` and `quiz_bank.json` references the same mixed-case ID; confirm `ExerciseAuthor.draft()` currently returns the fallback text.
2. Lowercase tags before looking them up in `concept_summaries`, ensuring we don’t mutate the original tag casing when rendering titles.
3. Add a regression test in `tests/test_exercise_author.py` that seeds a mixed-case concept ID and asserts the generated exercise uses the proper summary.
4. Run `pytest tests/test_exercise_author.py -q`.
5. Communicate progress via Agent Mail thread `ccopilot-hphj`, release reservations, and close the bead.

## Progress
- 2025-11-13 20:40 UTC – Plan drafted; reproduction pending.
- 2025-11-13 20:48 UTC – Reproduced: quizzes referencing `ACIDConcept` in mixed case fell back to the default expected outcome even though concepts.yaml defined a summary.
- 2025-11-13 20:55 UTC – Lowercased learning objective tags before summary lookup, provided a default summary when quizzes omit objectives, and added `test_exercise_author_uses_case_insensitive_concepts`; `pytest tests/test_exercise_author.py -q` → 3 passed.
