# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the CourseGen PoC (Proof of Concept) for Concepedia, implementing a Teacher RLM (Recursive Language Model) that orchestrates TA agents inside a DSPy CodeAct sandbox. The system generates course materials grounded by a handcrafted Database Systems world model and publishes artifacts to an Open Notebook instance.

## Key Architecture Components

### Core Pipeline Flow
1. **Teacher RLM** (`apps/orchestrator/teacher.py`) - Main orchestrator using vendored RLM package
2. **TA Roles** (`apps/orchestrator/ta_roles/`) - Specialized agents for syllabus design, lecture authoring, etc.
3. **CodeAct Sandbox** (`apps/codeact/`) - DSPy-based tool execution environment
4. **World Model** (`outputs/world_model/`) - SQLite database with concepts, papers, timeline, claims
5. **Scientific Evaluation** - Hypothesis-driven development and Bayesian uncertainty quantification
6. **Open Notebook Export** - Course artifacts published to external notebook API

### Scientific Evaluation Modules
The system includes rigorous scientific evaluation capabilities:

**Hypothesis Generation** (`apps/codeact/hypothesis_generator.py`)
- HypoGeniC framework integration for pedagogical hypothesis testing
- Category-based hypothesis testing: content ordering, difficulty progression, engagement, assessment, cognitive load
- Fallback hypothesis generation when hypogenic package unavailable
- Hypothesis refinement through iterative testing

**Scientific Evaluator** (`apps/orchestrator/scientific_evaluator.py`)
- Bloom's taxonomy alignment scoring
- Learning path coherence measurement
- Citation validity and coverage analysis
- Readability assessment (Flesch-Kincaid metrics)
- Retention and engagement predictions
- Configurable per-metric toggles via `config/scientific_config.yaml`

**Belief Network** (`world_model/belief_network.py`)
- Bayesian confidence scoring for knowledge claims
- Contradiction detection using semantic heuristics
- Evidence accumulation and belief updating
- Confidence decay over time
- Multiple resolution strategies (highest confidence, most recent, merge)

**Configuration** (`config/scientific_config.yaml`)
- Unified configuration for all scientific features
- Hypothesis testing settings (method, num_hypotheses, refinement_iterations)
- Evaluation metric toggles and thresholds
- Reproducibility settings (seeds, deterministic mode, caching)
- World model integration (confidence scores, contradiction detection)

### Model Configuration
The system uses three distinct model handles configured in `config/pipeline.yaml`:
- **teacher**: Main RLM orchestrator (typically GPT-4)
- **ta**: Teaching assistant agents (GPT-4o-mini)
- **student**: Student graders for evaluation (GPT-4o-mini)

Each role resolves credentials in priority order:
1. Optional `api_key_env` field
2. Role-specific env var (e.g., `OPENAI_API_KEY_TA`)
3. Global `OPENAI_API_KEY`

## Issue Tracking with bd (beads)

**IMPORTANT**: This project uses **bd (beads)** for ALL issue tracking. Do NOT use markdown TODOs, task lists, or other tracking methods.

### Why bd?

- Dependency-aware: Track blockers and relationships between issues
- Git-friendly: Auto-syncs to JSONL for version control
- Agent-optimized: JSON output, ready work detection, discovered-from links
- Prevents duplicate tracking systems and confusion

### Quick Start

**Check for ready work:**
```bash
bd ready --json
```

**Create new issues:**
```bash
bd create "Issue title" -t bug|feature|task -p 0-4 --json
bd create "Issue title" -p 1 --deps discovered-from:bd-123 --json
```

**Claim and update:**
```bash
bd update bd-42 --status in_progress --json
bd update bd-42 --priority 1 --json
```

**Complete work:**
```bash
bd close bd-42 --reason "Completed" --json
```

### Issue Types

- `bug` - Something broken
- `feature` - New functionality
- `task` - Work item (tests, docs, refactoring)
- `epic` - Large feature with subtasks
- `chore` - Maintenance (dependencies, tooling)

### Priorities

- `0` - Critical (security, data loss, broken builds)
- `1` - High (major features, important bugs)
- `2` - Medium (default, nice-to-have)
- `3` - Low (polish, optimization)
- `4` - Backlog (future ideas)

### Workflow for AI Agents

1. **Check ready work**: `bd ready` shows unblocked issues
2. **Claim your task**: `bd update <id> --status in_progress`
3. **Work on it**: Implement, test, document
4. **Discover new work?** Create linked issue:
   - `bd create "Found bug" -p 1 --deps discovered-from:<parent-id>`
5. **Complete**: `bd close <id> --reason "Done"`
6. **Commit together**: Always commit the `.beads/issues.jsonl` file together with the code changes so issue state stays in sync with code state

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Commit code regularly—at minimum once per bead—and include the bead id in each commit message
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems

## Multi-Agent Coordination with MCP Agent Mail

### What it is

- A mail-like layer that lets coding agents coordinate asynchronously via MCP tools and resources
- Provides identities, inbox/outbox, searchable threads, and advisory file reservations, with human-auditable artifacts in Git

### Why it's useful

- Prevents agents from stepping on each other with explicit file reservations (leases) for files/globs
- Keeps communication out of your token budget by storing messages in a per-project archive
- Offers quick reads (`resource://inbox/...`, `resource://thread/...`) and macros that bundle common flows

### How to use effectively

1. **Register an identity**:
   - Call `ensure_project` using this repo's absolute path as `project_key`
   - Call `register_agent` with your agent name (use adjective+noun format like "BlueLake", "GreenCastle")

2. **Reserve files before editing**:
   ```
   file_reservation_paths(project_key, agent_name, ["src/**"], ttl_seconds=3600, exclusive=true)
   ```

3. **Communicate with threads**:
   - Use `send_message(..., thread_id="bd-123")` to link messages to beads issues
   - Check inbox with `fetch_inbox`
   - Acknowledge with `acknowledge_message`

4. **Read fast**:
   - `resource://inbox/{Agent}?project=<abs-path>&limit=20`
   - `resource://thread/{id}?project=<abs-path>&include_bodies=true`

### Integration with Beads

**Single source of truth**: Use **Beads** for task status/priority/dependencies; use **Agent Mail** for conversation, decisions, and attachments.

**Shared identifiers**: Use the Beads issue id (e.g., `bd-123`) as the Mail `thread_id` and prefix message subjects with `[bd-123]`.

**Typical flow**:
1. **Pick ready work** (Beads): `bd ready --json` → choose one item
2. **Reserve edit surface** (Mail): `file_reservation_paths(..., reason="bd-123")`
3. **Announce start** (Mail): `send_message(..., thread_id="bd-123", subject="[bd-123] Start: <title>", ack_required=true)`
4. **Work and update**: Reply in-thread with progress and attach artifacts
5. **Complete and release**:
   - `bd close bd-123 --reason "Completed"`
   - `release_file_reservations(...)`
   - Final Mail reply: `[bd-123] Completed` with summary

### Macros vs Granular Tools

- **Prefer macros for speed**: `macro_start_session`, `macro_prepare_thread`, `macro_file_reservation_cycle`, `macro_contact_handshake`
- **Use granular tools for control**: `register_agent`, `file_reservation_paths`, `send_message`, `fetch_inbox`, `acknowledge_message`

### Important Coordination Rules

- ✅ Register with Agent Mail at the start of each session
- ✅ Check inboxes at the start/end of each session and after major updates
- ✅ Use `bd-###` as `thread_id` for all issue-related messages
- ✅ Reserve files before editing to prevent conflicts
- ✅ Release reservations when done
- ✅ Send timely status messages so other agents stay aligned
- ❌ Do NOT edit files without reserving them first
- ❌ Do NOT ignore inbox messages from other agents

## Development Commands

### Installation
```bash
# Create Python 3.11+ environment and install
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Initialize vendor submodules
git submodule update --init --recursive

# Install git hooks (recommended)
./scripts/install-hooks.sh
```

### Git Hooks

This repository includes automated git hooks for code quality and consistency:

**Install hooks:**
```bash
# Install all hooks (interactive)
./scripts/install-hooks.sh

# Force install (overwrite existing)
./scripts/install-hooks.sh --force
```

**Available hooks:**

- **pre-commit**: Runs before commits to:
  - Sync bd (beads) issues to `.beads/issues.jsonl`
  - Format Python files with `ruff format`
  - Lint Python files with `ruff check --fix`
  - Format markdown/YAML/JSON with `prettier` (if available)
  - Auto-stage formatted files

- **commit-msg**: Validates commit message format:
  - Enforces conventional commits: `type(scope): subject`
  - Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
  - Example: `feat(auth): add user login`

- **pre-push**: Runs before push to:
  - Run `ruff check` (without auto-fix) to catch remaining issues
  - Check for potential sensitive data patterns
  - Optional: Run tests (disabled by default for speed)

- **post-merge**: Runs after merge/pull to:
  - Import updated bd issues from `.beads/issues.jsonl`
  - Notify about dependency changes (Python, Node)
  - Warn about config file updates

**Required tools:**
- `ruff` - Python formatting and linting (required)
  ```bash
  brew install ruff
  # or: pip install ruff
  ```

**Optional tools:**
- `prettier` - Markdown/YAML/JSON formatting
  ```bash
  brew install prettier
  # or: npm install -g prettier
  ```
- `ast-grep` - Structural code search
  ```bash
  brew install ast-grep
  ```
- `fastmod` - Code refactoring
  ```bash
  cargo install fastmod
  ```

**Bypassing hooks (use sparingly):**
```bash
# Skip pre-commit hook
git commit --no-verify -m "message"

# Skip pre-push hook
git push --no-verify
```

### Running the Main Pipeline
```bash
# Quick start with minimal configuration
python apps/orchestrator/run_poc.py \
  --constraints config/course_config.yaml \
  --concepts data/handcrafted/database_systems \
  --notebook database-systems-poc \
  --ablations no_students

# Full CLI with all options
coursegen-poc --config config/pipeline.yaml --dry-run

# With custom output directory
python apps/orchestrator/run_poc.py \
  --constraints config/course_config.yaml \
  --output-dir /tmp/coursegen-run
```

### World Model Management
```bash
# Validate handcrafted data
validate-handcrafted data/handcrafted/database_systems

# Rebuild world model snapshot
python scripts/ingest_handcrafted.py \
  data/handcrafted/database_systems \
  outputs/world_model/state.sqlite \
  --jsonl outputs/world_model/latest.jsonl

# Inspect world model data
wm-inspect concepts --topic transaction
wm-inspect timeline
wm-inspect artifacts --type quiz_bank
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cli_run_poc.py -v

# Run with coverage
pytest --cov=ccopilot --cov-report=html

# Run linting
ruff check .
ruff format .
```

### Grader CLI (Standalone)
```bash
# Re-run student graders without full pipeline
python -m apps.orchestrator.eval_loop --repo-root . --quiet
```

### Portal Backend
```bash
# Start the FastAPI observability server
uvicorn apps.portal_backend.main:app --reload --port 8001

# Frontend (in separate terminal)
cd frontend
pnpm install  # or npm install
pnpm dev      # starts on http://localhost:3000
```

## Project Structure

### Input Configuration
- `config/course_config.yaml` - Course constraints (duration, objectives, sources)
- `config/pipeline.yaml` - Model settings and orchestration config
- `data/handcrafted/database_systems/` - Handcrafted world model data

### Generated Outputs
- `outputs/course_plan.md` - Generated course syllabus
- `outputs/lectures/*.md` - Individual lecture content
- `outputs/world_model/state.sqlite` - Compiled world model database
- `outputs/evals/run-*.jsonl` - Student evaluation results
- `outputs/artifacts/run-*-highlights.json` - Concept/timeline slices
- `outputs/logs/teacher-trace-*.json` - Teacher RLM execution trace

### Test Structure
- Tests use `unittest` with mock notebook API (`tests/mocks/notebook_api.py`)
- World model tests validate ingestion and query operations
- CLI tests check end-to-end pipeline execution with various ablations

## Environment Variables

### Required
- `OPENAI_API_KEY` - OpenAI API key (or role-specific variants)

### Optional
- `COURSEGEN_VENDOR_RLM_PATH` - Override vendored RLM package path
- `COURSEGEN_REPO_ROOT` - Repository root for CLI operations
- `OPEN_NOTEBOOK_API_BASE` - Notebook API endpoint
- `OPEN_NOTEBOOK_API_KEY` - Notebook API authentication
- `OPEN_NOTEBOOK_SLUG` - Target notebook identifier
- `OPEN_NOTEBOOK_AUTO_CREATE` - Auto-create notebooks (0/1)
- `OPEN_NOTEBOOK_EXPORT_DIR` - Local export directory
- `OPEN_NOTEBOOK_EXPORT_MIRROR` - Mirror API pushes to disk (0/1)
- `PORTAL_OUTPUTS_DIR` - Portal backend outputs directory
- `WORLD_MODEL_STORE` - Custom world model SQLite path

## Ablation Switches

Use `--ablations` flag to disable components:
- `no_students` - Skip student grader evaluation
- `no_world_model` - Use raw handcrafted data instead of SQLite
- `no_recursion` - Run teacher in single-agent mode

## CodeAct Tool Registry

Key world model tools available in the sandbox:
- `wm_get_concepts(topic, depth)` - Query concept taxonomy
- `wm_search_events(query)` - Search timeline events
- `run_sql(query)` - Execute DuckDB queries
- `lookup_paper(paper_id)` - Retrieve paper citations
- `record_claim(concept_id, content, citations)` - Add claims to world model
- `push_notebook_section(notebook, section)` - Export to Open Notebook
- `grade_module(module_md, rubric_id)` - Run student evaluation

## Common Development Patterns

### Adding New TA Roles
1. Create new role module in `apps/orchestrator/ta_roles/`
2. Implement role-specific prompts and logic
3. Register in teacher's spawn_ta helper
4. Add corresponding CodeAct programs if needed

### Extending World Model
1. Add data files to `data/handcrafted/database_systems/`
2. Run validation: `validate-handcrafted data/handcrafted/database_systems`
3. Rebuild snapshot with ingestion script
4. Update relevant tools in `apps/codeact/tools/`

### Testing with Mock Notebook API
```python
from tests.mocks.notebook_api import NotebookAPIMock

# In test setup
self.notebook_api = NotebookAPIMock()
with self.notebook_api.patch_open_notebook_client():
    # Run code that uses notebook API
    pass
```

## Debugging Tips

1. Use `--dry-run` to test configuration without running expensive operations
2. Check `outputs/logs/provenance.jsonl` for detailed execution traces
3. Inspect `outputs/artifacts/run-*-highlights.json` for world model usage
4. Use `--quiet` flag to suppress progress hints when scripting
5. Set `COURSEGEN_VENDOR_RLM_PATH` to test against experimental RLM branches
6. Portal UI at http://localhost:3000 provides real-time run visualization