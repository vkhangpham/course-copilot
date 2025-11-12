# Plan – ccopilot-eiv (Fix duplicated graph citation validation)

## Goal
`scripts/handcrafted_loader.validate_dataset` iterates over each edge's citations twice, which emits duplicate errors for the same missing paper and makes the validation logs noisy. Clean up the logic so each citation is checked exactly once while preserving the rest of the validation semantics.

## Steps
1. Reproduce the duplicate error by crafting a minimal dataset sample (unit test) that includes a graph edge referencing an unknown paper.
2. Update `validate_dataset` to deduplicate the citation loop and reuse a helper so tests cover the regression.
3. Run the relevant test slice (new test + affected modules) to ensure coverage and no regressions.
4. Update bead + communicate via Agent Mail once complete.

## Progress
- 2025-11-12 09:57Z – GreenBear opened ccopilot-eiv, reserved the loader/test files, and started on the duplicate citation validation fix.
- 2025-11-12 09:59Z – Added regression in `tests/test_handcrafted_loader.py` ensuring unknown graph citations produce a single error, cleaned up `scripts/handcrafted_loader.py` to dedupe citation checks, and ran `pytest tests/test_handcrafted_loader.py -q` → 5 passed.
