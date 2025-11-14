# Plan – ccopilot-34tu (run_sql_query should block COPY/LOAD commands)

## Goal
Ensure the CodeAct `run_sql_query` helper truly stays read-only by rejecting COPY/LOAD/CALL/INSTALL/SET statements, preventing CodeAct programs from writing files or loading extensions.

## Steps
1. Confirm COPY/LOAD statements slip past `_is_mutating_statement` because `_READ_ONLY_PREFIXES` lacks those keywords.
2. Expand the guard keywords and add regression tests so COPY/LOAD/CALL/INSTALL/SET raise `ValueError` like other mutating statements.
3. Run `pytest tests/test_codeact_data.py` and communicate completion via Agent Mail.

## Progress
- 2025-11-13 04:59Z – Verified `COPY authors TO 'foo.csv'` executes successfully via `run_sql_query`, writing to disk despite the documented read-only contract.
- 2025-11-13 05:02Z – Added COPY/LOAD/CALL/INSTALL/SET to `_READ_ONLY_PREFIXES` and introduced `tests/test_codeact_data.py::test_run_sql_query_blocks_copy_and_load`. `pytest tests/test_codeact_data.py -q` passes (existing suite plus new parametrized test).
