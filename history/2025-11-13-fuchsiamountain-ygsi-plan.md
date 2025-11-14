# Plan – ccopilot-ygsi (Explainer timeline should split semicolon-separated concepts)

## Goal
`apps/orchestrator/ta_roles/explainer._load_timeline` currently splits the `related_concepts` CSV column on commas only. The handcrafted dataset encodes multiple concepts with semicolons (e.g., `relational_model;relational_algebra`), so timelines for individual concepts never attach to those entries. As a result history blurbs never surface for high-value concepts (relational_model, query_planning, etc.). Fix the parser so it treats both commas and semicolons as delimiters.

## Steps
1. Reproduce: instantiate `Explainer()` and confirm `_history_line("relational_model")` returns `(None, None)` even though the timeline CSV references that concept with a semicolon.
2. Update `_load_timeline` to split on either delimiter (use `re.split(r"[;,]", ...)`), trimming whitespace.
3. Add a regression test in `tests/test_explainer.py` that asserts `_history_line` (or the public `write` output) includes the 1970 relational-model event.
4. Run `pytest tests/test_explainer.py -q`.
5. Communicate via Agent Mail thread `ccopilot-ygsi`, release reservations, and close the bead.

## Progress
- 2025-11-13 12:17 UTC – Plan drafted; reproduction pending.
- 2025-11-13 12:22 UTC – Reproduced the bug (`Explainer()._history_line("relational_model")` returned `(None, None)`).
- 2025-11-13 12:25 UTC – Updated `_load_timeline` to split `related_concepts` on both commas and semicolons; added regression test `test_explainer_history_line_parses_semicolon_concepts`; `pytest tests/test_explainer.py -q` → 3 passed.
