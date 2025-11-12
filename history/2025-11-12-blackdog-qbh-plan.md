# Plan – ccopilot-qbh (NotebookPublisher should not duplicate heading text)

Issue: when using inline content or fetching markdown from files, `chunk_markdown_sections` keeps the original heading line in the section content, so when NotebookPublisher sends the section to Open Notebook the heading appears twice (once in the title, once at the top of the body). Need to strip the heading line from the section body.

Steps:
1. Update `chunk_markdown_sections` (and `build_sections_from_markdown` if needed) so each section’s content excludes the heading line that determined its title.
2. Extend `tests/test_notebook_publisher.py` to cover this behavior.
3. Run the notebook publisher test slice (and any dependent suites) to confirm.
4. Communicate + close bead.

## Progress
- 2025-11-12 09:44Z – GreenBear reopened ccopilot-qbh, claimed it, and is preparing the NotebookPublisher heading dedup fix.
- 2025-11-12 09:52Z – Added BOM/zero-width stripping to NotebookPublisher heading detection plus regression tests to keep section bodies free of duplicate headings; `pytest tests/test_notebook_publisher.py -q` ⇒ 12 passed.
