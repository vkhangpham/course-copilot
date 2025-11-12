# Plan – ccopilot-m76 (NotebookPublisher ignores setext headings)

## Goal
`chunk_markdown_sections` only recognizes ATX headings (`# ...`). Any markdown artifact using setext headings (text followed by `===`/`---`) collapses into the fallback section, so Notebook exports duplicate the heading inside the body and lose section splits. Need to teach the chunker/title derivation to detect setext forms and add regression coverage.

## Steps
1. Add tests in `tests/test_notebook_publisher.py` covering setext titles for both chunking and `_derive_title`.
2. Update `apps/orchestrator/notebook_publisher.py` to detect setext headings when chunking (including stripping the heading line from section content) and when deriving fallback titles.
3. Run `pytest tests/test_notebook_publisher.py -q`.
4. Update plan + bead, communicate via Agent Mail.

## Progress
- 2025-11-12 11:07Z – GreenBear opened ccopilot-m76, reserved the notebook publisher/test files, and started on setext heading support.
- 2025-11-12 11:09Z – Added setext-aware heading detection/tests for NotebookPublisher and ran `pytest tests/test_notebook_publisher.py -q` → 14 passed.
