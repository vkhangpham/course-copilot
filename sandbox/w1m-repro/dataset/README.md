# Database Systems knowledge assets

This directory contains the handcrafted symbolic world model used by the CourseGen PoC.

## Contents

| File | Purpose |
| --- | --- |
| `taxonomy.yaml` | Domain + module taxonomy mapping concept IDs to weekly themes. |
| `concepts.yaml` | Canonical concepts with parent relationships, prerequisites, and citations. |
| `graph.yaml` | Additional semantic edges (prerequisites, enables, informs). |
| `definitions.yaml` | Claim-level statements tied to citations. |
| `timeline.csv` | Chronological milestones with concept + citation references. |
| `papers.csv` / `authors.csv` | Bibliography for citations referenced throughout the dataset. |
| `quiz_bank.json` | Rubric-aligned quiz items used by student graders. |
| `course_outline.yaml` | Eight-week course outline linking modules, concepts, and readings. |
| `manifest.yaml` | Helper manifest describing files + ingestion command. |

## Usage

1. Validate the dataset before ingesting:

   ```bash
   validate-handcrafted data/handcrafted/database_systems
   ```

2. Populate the SQLite world model (and optional JSONL snapshot):

   ```bash
   python scripts/ingest_handcrafted.py \
     data/handcrafted/database_systems \
     outputs/world_model/state.sqlite \
     --jsonl outputs/world_model/snapshot.jsonl
   wm-inspect concepts --store outputs/world_model/state.sqlite --topic transaction
   ```

The validation step fails fast when IDs/citations drift, and the ingestion script then writes
the clean dataset into the shared world model store so the Teacher RLM + CodeAct tools can query it.
