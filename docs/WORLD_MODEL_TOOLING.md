# World-Model Tooling Guide

This note explains how to maintain and inspect the handcrafted Database Systems world model
(described in `docs/PLAN.md` §4/§9). The same workflow should be used any time you edit
`data/handcrafted/database_systems/` or need to regenerate the SQLite snapshot consumed by the
orchestrator/CodeAct tools.

## Directory structure

```
data/handcrafted/database_systems/
├── taxonomy.yaml            # Domains/modules → concept IDs
├── concepts.yaml            # Canonical concept metadata, parents, prerequisites, citations
├── graph.yaml               # Additional edges (prerequisite, enables, complements, ...)
├── definitions.yaml         # Citeable claims linked to concept IDs
├── timeline.csv             # Milestones referencing concepts + citations
├── papers.csv / authors.csv # Bibliography used for grounding
├── quiz_bank.json           # Rubric-aligned quiz items
├── course_outline.yaml      # Optional outline used by the Teacher RLM
└── manifest.yaml            # (Optional) helper metadata for ops tooling
```

All IDs are lowercase snake_case and must match across files (concepts ↔ taxonomy ↔ quiz ↔ timeline).

## Common commands

> **Note:** `wm-inspect` automatically targets `outputs/world_model/state.sqlite` from the repo root. When you run the CLI outside this checkout, export `COURSEGEN_REPO_ROOT=/abs/path/to/ccopilot` so auto-detection still lands inside your repo. Use the `--store` flag or `WORLD_MODEL_STORE` env var when pointing at an alternate snapshot—the CLI re-resolves those env vars every time a command executes, so you can set them immediately before invoking the tool even if it was imported earlier (e.g., inside tests).

| Action | Command |
| ------ | ------- |
| Validate dataset | `validate-handcrafted data/handcrafted/database_systems` |
| Ingest snapshot | `python scripts/ingest_handcrafted.py data/handcrafted/database_systems outputs/world_model/state.sqlite --jsonl outputs/world_model/snapshot.jsonl` |
| Inspect concepts | `wm-inspect concepts --topic transaction` |
| List timeline events | `wm-inspect timeline --concept transactions --year 2012` |
| List papers | `wm-inspect papers --keyword relational --year 1970` |
| List authors | `wm-inspect authors --keyword stonebraker` |
| Show definitions | `wm-inspect definitions --concept transaction_management` |
| Inspect graph edges | `wm-inspect graph --concept relational_model` |
| Inspect stored artifacts | `wm-inspect artifacts --type quiz_bank` |
| Run orchestrator with fresh ingest | `coursegen-poc --config config/pipeline.yaml --ingest-world-model` |

> **CodeAct note:** the CodeAct world-model tools (`fetch_concepts`, `search_events`, etc.) now follow the same rules.
> If `WORLD_MODEL_STORE` is unset, they fall back to `COURSEGEN_REPO_ROOT/outputs/world_model/state.sqlite`. This lookup happens at execution time, so library callers and tests can flip env vars between invocations without reloading the module.
> means automation or REPL sessions running outside the repo only need to export `COURSEGEN_REPO_ROOT`, and every tool
> (CLI + CodeAct) will resolve paths consistently.

The `coursegen-poc` CLI also accepts `--dataset-dir` and `--world-model-store` if you need to point
at alternate datasets or snapshots.

## Validation pipeline

1. **Edit the dataset** – keep IDs consistent and cite sources listed in `papers.csv`.
2. **Run the validator** – `validate-handcrafted …` fails fast on missing IDs, duplicate authors,
   timeline concept drift, etc. Fix issues before ingesting or committing.
3. **Ingest** – the ingestion CLI rewrites `outputs/world_model/state.sqlite` and emits a JSONL snapshot
   that is easy to diff in reviews. The orchestrator will log dataset summaries and warn if the
   snapshot is missing.

## Troubleshooting

- **Missing concept errors** – check `concepts.yaml` for typos; the validator enumerates the IDs it
  expected. Use `wm-inspect concepts --store ...` to confirm ingestion results.
- **SQLite not regenerating** – ensure the destination directory exists (the ingest command now
  creates parent directories) and that another agent doesn’t hold a reservation on the file.
- **CLI can’t find dataset** – pass `--dataset-dir /path/to/dataset` when running `coursegen-poc` or
  set the path in `config/pipeline.yaml` under `world_model.dataset_dir`.
- **Need a quick sample** – `wm-inspect timeline --year 2012`
  (or combine with `--concept relational_model`) prints JSON rows filtered by the
  provided arguments.

Ping `ccopilot-o78` owners in Agent Mail if the schema needs to evolve; remember to rerun the
validation + ingestion commands before committing.
