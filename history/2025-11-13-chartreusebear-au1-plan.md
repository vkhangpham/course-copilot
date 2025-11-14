# Plan – ccopilot-au1 (Timeline ingest should parse comma-separated related concepts)

## Goal
`ingest_handcrafted._split_list` only separates `related_concepts` on semicolons, so CSV rows that use commas collapse into a single concept id and bypass validation. Update the parser to treat commas and semicolons as equivalent and add regression tests covering both `_load_datasets` and ingestion behavior.

## Steps
1. Reproduce the issue by copying the handcrafted dataset, swapping timeline delimiters to commas, and running `_load_datasets` to confirm concept_ids collapses to one entry.
2. Update `_split_list` (and any downstream references) to split on comma/semicolon and trim whitespace; import `re` if helpful.
3. Add a regression test in `tests/test_ingest_handcrafted.py` that writes a dataset with comma-separated related_concepts and asserts `concept_ids` includes both ids.
4. Run targeted pytest (`tests/test_ingest_handcrafted.py -k related_concepts`) and document results.
5. Update history + notify via Agent Mail thread `ccopilot-au1`.

## Progress
- 2025-11-13 01:13Z – ChartreuseBear filed ccopilot-au1 after code review showed `_split_list` only handles `;` even though docs expect comma/semicolon support.
- 2025-11-13 01:15Z – Reproduced the failure by copying `data/handcrafted` to a sandbox, swapping `related_concepts` delimiters to commas, and hitting `ValueError: unknown concept relational_model,relational_algebra`.
- 2025-11-13 01:19Z – Updated `_split_list` to split on `[;,]`, added `test_load_datasets_accepts_comma_delimited_related_concepts`, and ran `pytest tests/test_ingest_handcrafted.py -q` (7 passed).
