# Plan · ccopilot-j9qz – Belief network contradictions

## Context
- New `BayesianBeliefNetwork` checks for contradictions when claims are added.
- The default path sets `existing_claims=[]`, so unless callers pass their own list, no comparisons occur.
- BeliefState doesn’t store claim text, so even if we iterated through beliefs we couldn’t compare content.

## Steps
1. **Persist content** – extend `BeliefState` to keep the claim content and include it in `to_dict()`.
2. **Default existing claims** – when `existing_claims` is omitted, build it from `self.beliefs` so new claims are checked against prior ones, and update the older belief’s `contradictions` list when a conflict is found.
3. **Regression test** – add a unit/integration test to `tests/test_scientific_integration.py` proving that contradictory claims are detected automatically.
