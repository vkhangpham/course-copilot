# Scripts

| Command | Description |
| ------- | ----------- |
| `validate-handcrafted data/handcrafted/database_systems` | Typer CLI that loads the dataset via `scripts/handcrafted_loader.py`, checking citations, timelines, and quiz references before ingestion. |
| `python scripts/ingest_handcrafted.py DATA_DIR world_model/state.sqlite --jsonl outputs/world_model/snapshot.jsonl` | Rebuilds the SQLite world model and optional JSONL snapshot. The `--ingest-world-model` flag on `coursegen-poc` calls this under the hood. |
| `wm-inspect concepts --store world_model/state.sqlite --topic transaction` | Ad-hoc inspector for concepts/timeline/claims stored in SQLite (handy when tuning prompts). |
| `coursegen-poc --help` | Main orchestrator CLI (see `ccopilot/cli/run_poc.py`). |

Additional automation scripts (evaluation loop, dataset sampling) will live here once implemented.
