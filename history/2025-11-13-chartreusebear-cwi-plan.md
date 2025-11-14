# Plan – ccopilot-cwi (Student grader should skip required source checks when config omits them)

## Goal
`StudentGraderPool` builds default source keywords (Codd/System R) even when the course config doesn’t list required sources. That causes the grounding rubric to fail unless every lecture mentions those defaults, contradicting the config contract. Remove the implicit defaults so source checks only run when `required_sources` is provided, and add regression tests covering both configured/not-configured behaviors.

## Steps
1. Reproduce by running `StudentGraderPool.from_yaml(..., required_sources=None)` against an artifact without citations and confirm `_check_required_sources` still fails.
2. Update `_build_source_keyword_map` to return `{}` when `sources` is falsy (no defaults) and ensure `_check_required_sources` short-circuits.
3. Add/adjust unit tests in `tests/test_students.py` verifying (a) missing required sources is flagged when configured, and (b) omission passes when no sources are provided.
4. Run `pytest tests/test_students.py -q` and document the result.
5. Update plan + mail thread `ccopilot-cwi` with the fix summary.

## Progress
- 2025-11-13 01:22Z – ChartreuseBear opened bead after code review found default source enforcement ignoring config.
- 2025-11-13 01:23Z – Confirmed `StudentGraderPool.from_yaml` builds `_source_keywords={'codd', 'system r'}` even when `required_sources` is empty, reproducing the unintended rubric failures.
- 2025-11-13 01:27Z – Updated `_build_source_keyword_map` to return `{}` when no required sources are configured, added `test_student_grader_pool_without_required_sources_does_not_require_defaults`, and ran `pytest tests/test_students.py -q` (6 passed).
