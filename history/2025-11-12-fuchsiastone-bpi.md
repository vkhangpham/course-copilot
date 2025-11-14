# Notebook Publisher Tests (2025-11-12 · FuchsiaStone)

- Added `tests/test_notebook_publisher.py` covering citation extraction, title derivation, and the publish flow using a stubbed `push_notebook_section` so we can exercise the Open Notebook export path offline.
- Reused the existing push_notebook_section mock infrastructure—no runtime changes required.
- To run just these checks: `pytest tests/test_notebook_publisher.py`.
