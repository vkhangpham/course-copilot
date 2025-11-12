# Plan – ccopilot-abu (Track orchestrator student/notebook helpers)

Problem: several orchestrator helper modules (`apps/orchestrator/notebook_publisher.py`, `.../student_loop.py`, `.../student_qa.py`) plus the handcrafted quiz bank (`data/quiz.json`) exist in the workspace but are still untracked. Tests and runtime imports depend on them, so a clean checkout would fail immediately.

Steps:
1. Verify the helper modules and quiz asset match the versions currently imported in tests (no local diffs vs. executed code).
2. Add the files to git with sensible locations (and ensure package `__all__` / exports align).
3. Run the relevant test suites (`pytest tests/test_students.py tests/test_portal_backend.py -q`) to confirm everything still passes from a clean tree.
4. Communicate + close the bead once committed.
