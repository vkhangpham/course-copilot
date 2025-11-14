# Plan – ccopilot-w1m (Paper author parsing should accept comma delimiters)

## Goal
`scripts/ingest_handcrafted._load_datasets` currently splits the `authors.csv` references using `field.split(';')`. If a `papers.csv` row uses commas (or mixed delimiters), ingestion collapses multiple authors into one token and raises "unknown author" errors. Update the parser to accept both comma and semicolon delimiters, mirroring the timeline fix.

## Steps
1. Reproduce by copying the dataset, replacing the `papers.csv` author delimiter with commas, and running `_load_datasets` to confirm it fails.
2. Update the parsing logic to split on `[;,]` (or reuse `_split_list`) and ensure whitespace is trimmed.
3. Add regression tests in `tests/test_ingest_handcrafted.py` covering both comma-delimited authors and mixed delimiters.
4. Run `pytest tests/test_ingest_handcrafted.py -k authors -q` (and full file) and document results + Agent Mail note.

## Progress
- 2025-11-13 02:38Z – Plan drafted; working on reproduction next.
- 2025-11-13 02:39Z – Reproduced by copying the dataset and replacing `papers.csv` delimiters with commas; `_load_datasets` raised `ValueError: Paper system-r-1976 references unknown authors: ['chamberlin,boyce']`.
- 2025-11-13 02:41Z – Updated `_load_datasets` to split author lists on `[;,]`, added `test_load_datasets_accepts_comma_delimited_authors`, and ran `pytest tests/test_ingest_handcrafted.py -q` (8 passed).
