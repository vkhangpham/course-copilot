## Project Overview

**Mission.** Build a reproducible Concepedia “CourseGen” proof of concept where a Teacher RLM orchestrates TA sub-agents to read a handcrafted Database Systems world model, plan a course, draft a lecture/study guide, self-evaluate with simulated students, and publish grounded materials into Open Notebook. The high-level goal, success criteria, and acceptance tests live in `docs/PLAN.md` (Sections 0–3) and `docs/PoC.md` (Sections 1–3).

**End-to-end outcome.** One CLI entry point should run the full pipeline—from ingesting YAML/CSV concept graphs through Notebook export—and emit (a) a multi-week course plan, (b) at least one fully cited lecture module, (c) evaluation artifacts (grader scores, agent trace, provenance), and (d) toggles for ablations (disable recursion, students, or world model) to prove each subsystem’s impact (`docs/PLAN.md`, “Goal & Success Criteria”).

**System pillars.**

- **Recursive Language Model (RLM) teacher loop.** The orchestrator treats prompts as mutable state, can spawn depth-1 subcalls, and interacts with an external REPL to inspect arbitrarily large contexts, letting us dodge context-rot while coordinating TA roles (`docs/PLAN.md` §1; `docs/PoC.md` “System Overview”; `docs/Recursive Language Models (RLM)_ Concept, Applications, and Implementation.pdf`). The default REPL lives under `vendor/rlm`, but you can point the teacher loop at another checkout by exporting `COURSEGEN_VENDOR_RLM_PATH=/absolute/path/to/rlm` before running the CLI.
- **DSPy CodeAct sandbox.** Every “think with code” action runs through CodeAct signatures that wrap pure tool functions (world-model CRUD, DuckDB/SQLite queries, Open Notebook client). CodeAct’s iterative code→execute→reflect loop is detailed in `docs/__CodeAct Module (DSPy)__ – Technical & Strategic Analysis.pdf` and underpins TA autonomy.
- **Symbolic world model.** A structured concept graph (entities, relationships, provenance) is the coordination bus for agents, inspired by Kosmos-style research loops and the symbolic world-model blueprint in `docs/Symbolic World Models in a Sandboxed Academic Knowledge Domain.pdf`. Agents read/write it via CodeAct tools to keep long-horizon coherence.
- **Self-evolving grader loop.** Simulated “student” agents evaluate plans and lectures with rubric-driven checks; failing cases trigger prompt/policy mutation before artifacts ship. See `docs/OpenAI __Self-Evolving Agents__ – Autonomous Agent Retraining Deep-Dive.pdf` and `docs/PLAN.md` (Phase C) for the mutation workflow.
- **NotebookLM/Open Notebook publishing.** Final artifacts are grounded, cited, and pushed into a locally hosted Open Notebook instance (Next.js + FastAPI + SurrealDB). Architectural and deployment details are summarized in `docs/Notebook LM in Education_ Vision and Open Notebook Implementation.pdf` and referenced runbooks in `docs/PoC.md` §§2–4.

**Scope & data (v0).** The initial domain is _Database Systems_. Inputs are handcrafted YAML/CSV taxonomies, timelines, seminal papers, and quiz banks under `data/` (see placeholders in `docs/PLAN.md` §2 and Appendix A). Until our own schemas solidify, use the adjacent reference repositories as inspiration: taxonomy samples under `../taxonomy/data/last_runs/` and timeline outputs under `../timeline/results/fixed/`. All agents have read access to those folders (symlinks into this repo are allowed), so borrow structure/examples directly rather than duplicating content. Everything else (papers, authors, relationships, quiz bank) must be authored from scratch according to the PRD. Constraints (audience level, tone, required sources) will live in `config/course_config.yaml`/`constraints.yaml`. Outputs land in `outputs/course_plan.md`, `outputs/lectures/`, and the Open Notebook notebook `database-systems-poc`.

- **Operational expectations.**
- Tooling: Python 3.11+, Node 18+, Deno (for DSPy), plus local `.env` wiring for OpenAI, OpenAlex, arXiv, and Open Notebook endpoints (`docs/PoC.md` §1–2). DSPy now prefers role-specific keys when present (`OPENAI_API_KEY_TEACHER`, `OPENAI_API_KEY_TA`, etc.) and falls back to the global `OPENAI_API_KEY`. CodeAct automatically uses the TA handle for Plan/Lecture/Citation programs, so **do not** reconfigure `dspy.settings` manually in agent code—set the env vars instead. Set `COURSEGEN_VENDOR_RLM_PATH` if you need the teacher REPL to load from somewhere other than `vendor/rlm`. **Important:** `.env` in the repo already contains real credentials—never edit or commit changes to it; consume the values as-is and keep secrets out of version control.
- Workflow: initialize submodules (`vendor/rlm`, `vendor/open-notebook`), rely on the handcrafted dataset in `data/handcrafted/database_systems`, run `python apps/orchestrator/run_poc.py ...`, then evaluate via `python apps/orchestrator/eval_loop.py ...` (`docs/PoC.md` “Execution Plan”).
- Logging & artifacts: persist world-model snapshots, agent traces, grader outputs, and Notebook IDs alongside the generated content for reproducibility (`docs/PLAN.md` “What “done” looks like”).
- CLI: keep the initial `apps/orchestrator/run_poc.py` interface minimal—only accept the constraint file, concept data path, notebook name, and an optional ablation flag per `docs/PLAN.md` toggles. Add richer model overrides later once the core loop works. Both this shim and the canonical `ccopilot.cli.run_poc` resolve every relative flag against the supplied `--repo-root`, so automation can invoke them from any working directory without juggling `cd` or symlinks.

**Research influences.** The architecture is anchored in external research that is mirrored inside `docs/` for quick onboarding: Kosmos AI Scientist for multi-agent world-model orchestration (`docs/Kosmos AI Scientist_ Multi‑Agent System with World Model Orchestrator.pdf`), Recursive Language Models for unbounded-context reasoning, DSPy CodeAct for safe tool calling, Self-Evolving Agents for automated prompt evolution, and NotebookLM/Open Notebook for grounded educational UX. New contributors should skim those PDFs before making architectural changes.

**Current status.** This repo currently contains documentation, planning assets, and a scaffolding `main.py`. There are no open bd issues yet (`bd ready --json` returns empty), so your first action after onboarding is to capture the initial implementation work in bd and sync it with `.beads/issues.jsonl`. Near-term work that must be turned into bd issues includes: (a) scaffolding the proposed directories/apps (`apps/orchestrator`, `data/`, `config/`, `vendor/` submodules), (b) authoring the handcrafted Database Systems knowledge assets (taxonomy YAML, timelines, quiz bank, constraints), and (c) codifying the single CLI entry point (`python apps/orchestrator/run_poc.py ...`) plus evaluation hooks described in `docs/PoC.md`. Track each item explicitly in bd before writing code so the task history stays auditable.

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

### Auto-Sync

bd automatically syncs with git:

- Exports to `.beads/issues.jsonl` after changes (5s debounce)
- Imports from JSONL when newer (e.g., after `git pull`)
- No manual export/import needed!

### MCP Server (Recommended)

If using Claude or MCP-compatible clients, install the beads MCP server:

```bash
pip install beads-mcp
```

Add to MCP config (e.g., `~/.config/claude/config.json`):

```json
{
  "beads": {
    "command": "beads-mcp",
    "args": []
  }
}
```

Then use `mcp__beads__*` functions instead of CLI commands.

### Managing AI-Generated Planning Documents

AI assistants often create planning and design documents during development:

- PLAN.md, IMPLEMENTATION.md, ARCHITECTURE.md
- DESIGN.md, CODEBASE_SUMMARY.md, INTEGRATION_PLAN.md
- TESTING_GUIDE.md, TECHNICAL_DESIGN.md, and similar files

**Best Practice: Use a dedicated directory for these ephemeral files**

**Recommended approach:**

- Create a `history/` directory in the project root
- Store ALL AI-generated planning/design docs in `history/`
- Keep the repository root clean and focused on permanent project files
- Only access `history/` when explicitly asked to review past planning

**Example .gitignore entry (optional):**

```
# AI planning documents (ephemeral)
history/
```

**Benefits:**

- ✅ Clean repository root
- ✅ Clear separation between ephemeral and permanent documentation
- ✅ Easy to exclude from version control if desired
- ✅ Preserves planning history for archeological research
- ✅ Reduces noise when browsing the project

### Important Rules

- ✅ Use bd for ALL task tracking
- ✅ Always use `--json` flag for programmatic use
- ✅ Link discovered work with `discovered-from` dependencies
- ✅ Check `bd ready` before asking "what should I work on?"
- ✅ Store AI planning docs in `history/` directory
- ❌ Do NOT create markdown TODO lists
- ❌ Do NOT use external issue trackers
- ❌ Do NOT duplicate tracking systems
- ❌ Do NOT clutter repo root with planning documents

For more details, see README.md and QUICKSTART.md.

## Overall rule

- Before doing anything else, read ALL of AGENTS dot md and register with agent mail and introduce yourself to the other agents. Then coordinate on the remaining tasks left in beads progress with the other agents and come up with a game plan for splitting and reviewing the work. Coordinate via MCP Agent Mail: check inboxes at the start/end of each session and after major updates, and send timely status messages so other agents stay aligned on shared work.
- Commit code regularly—at minimum once per bead—and include the bead id in each commit message so the audit trail stays aligned with bd. Break long sessions into incremental commits instead of batching everything at the end.
- Delete unused or obsolete files when your changes make them irrelevant (refactors, feature removals, etc.), and revert files only when the change is yours or explicitly requested. If a git operation leaves you unsure about other agents' in-flight work, stop and coordinate instead of deleting.
- **Before attempting to delete a file to resolve a local type/lint failure, stop and ask the user.** Other agents are often editing adjacent files; deleting their work to silence an error is never acceptable without explicit approval.
- NEVER edit `.env` or any environment variable files—only the user may change them.
- Coordinate with other agents before removing their in-progress edits—don't revert or delete work you didn't author unless everyone agrees.
- Moving/renaming and restoring files is allowed.
- ABSOLUTELY NEVER run destructive git operations (e.g., `git reset --hard`, `rm`, `git checkout`/`git restore` to an older commit) unless the user gives an explicit, written instruction in this conversation. Treat these commands as catastrophic; if you are even slightly unsure, stop and ask before touching them. _(When working within Cursor or Codex Web, these git limitations do not apply; use the tooling's capabilities as needed.)_
- Never use `git restore` (or similar commands) to revert files you didn't author—coordinate with other agents instead so their in-progress work stays intact.
- Always double-check git status before any commit
- Keep commits atomic: commit only the files you touched and list each path explicitly. For tracked files run `git commit -m "<scoped message>" -- path/to/file1 path/to/file2`. For brand-new files, use the one-liner `git restore --staged :/ && git add "path/to/file1" "path/to/file2" && git commit -m "<scoped message>" -- path/to/file1 path/to/file2`.
- Quote any git paths containing brackets or parentheses (e.g., `src/app/[candidate]/**`) when staging or committing so the shell does not treat them as globs or subshells.
- When running `git rebase`, avoid opening editors—export `GIT_EDITOR=:` and `GIT_SEQUENCE_EDITOR=:` (or pass `--no-edit`) so the default messages are used automatically.
- Never amend commits unless you have explicit written approval in the task thread.
- Run long running tasks with tmux. Watch and read the logs regularly.
- DO NOT define functions or variables whose names start with an underscore unless they are Python dunder methods (e.g., `__init__`).
- Prefer Pydantic models over frozen dataclasses, especially within LLM/DSPy integrations.

## Agent Tool

### MCP Agent Mail: coordination for multi-agent workflows

What it is

- A mail-like layer that lets coding agents coordinate asynchronously via MCP tools and resources.
- Provides identities, inbox/outbox, searchable threads, and advisory file reservations, with human-auditable artifacts in Git.

Why it's useful

- Prevents agents from stepping on each other with explicit file reservations (leases) for files/globs.
- Keeps communication out of your token budget by storing messages in a per-project archive.
- Offers quick reads (`resource://inbox/...`, `resource://thread/...`) and macros that bundle common flows.

How to use effectively

1. Same repository
   - Register an identity: call `ensure_project`, then `register_agent` using this repo's absolute path as `project_key`.
   - Reserve files before you edit: `file_reservation_paths(project_key, agent_name, ["src/**"], ttl_seconds=3600, exclusive=true)` to signal intent and avoid conflict.

- Communicate with threads: use `send_message(..., thread_id="FEAT-123")`; check inbox with `fetch_inbox` and acknowledge with `acknowledge_message`.
- Read fast: `resource://inbox/{Agent}?project=<abs-path>&limit=20` or `resource://thread/{id}?project=<abs-path>&include_bodies=true`.
- Tip: set `AGENT_NAME` in your environment so the pre-commit guard can block commits that conflict with others' active exclusive file reservations.
- Stakeholders introduce themselves through MCP Agent Mail when they begin work—monitor your inbox at the start/end of every session and after major updates so you can align and respond quickly.

2. Across different repos in one project (e.g., Next.js frontend + FastAPI backend)
   - Option A (single project bus): register both sides under the same `project_key` (shared key/path). Keep reservation patterns specific (e.g., `frontend/**` vs `backend/**`).
   - Option B (separate projects): each repo has its own `project_key`; use `macro_contact_handshake` or `request_contact`/`respond_contact` to link agents, then message directly. Keep a shared `thread_id` (e.g., ticket key) across repos for clean summaries/audits.

Macros vs granular tools

- Prefer macros when you want speed or are on a smaller model: `macro_start_session`, `macro_prepare_thread`, `macro_file_reservation_cycle`, `macro_contact_handshake`.
- Use granular tools when you need control: `register_agent`, `file_reservation_paths`, `send_message`, `fetch_inbox`, `acknowledge_message`.

Common pitfalls

- "from_agent not registered": always `register_agent` in the correct `project_key` first.
- "FILE_RESERVATION_CONFLICT": adjust patterns, wait for expiry, or use a non-exclusive reservation when appropriate.
- Auth errors: if JWT+JWKS is enabled, include a bearer token with a `kid` that matches server JWKS; static bearer is used only when JWT is disabled.

3. Integrating with Beads (dependency-aware task planning)

Beads provides a lightweight, dependency-aware issue database and a CLI (`bd`) for selecting "ready work," setting priorities, and tracking status. It complements MCP Agent Mail's messaging, audit trail, and file-reservation signals. Project: [steveyegge/beads](https://github.com/steveyegge/beads)

Recommended conventions

- **Single source of truth**: Use **Beads** for task status/priority/dependencies; use **Agent Mail** for conversation, decisions, and attachments (audit).
- **Shared identifiers**: Use the Beads issue id (e.g., `bd-123`) as the Mail `thread_id` and prefix message subjects with `[bd-123]`.
- **Reservations**: When starting a `bd-###` task, call `file_reservation_paths(...)` for the affected paths; include the issue id in the `reason` and release on completion.

Typical flow (agents)

1. **Pick ready work** (Beads)
   - `bd ready --json` → choose one item (highest priority, no blockers)
2. **Reserve edit surface** (Mail)
   - `file_reservation_paths(project_key, agent_name, ["src/**"], ttl_seconds=3600, exclusive=true, reason="bd-123")`
3. **Announce start** (Mail)
   - `send_message(..., thread_id="bd-123", subject="[bd-123] Start: <short title>", ack_required=true)`
4. **Work and update**
   - Reply in-thread with progress and attach artifacts/images; keep the discussion in one thread per issue id
5. **Complete and release**
   - `bd close bd-123 --reason "Completed"` (Beads is status authority)
   - `release_file_reservations(project_key, agent_name, paths=["src/**"])`
   - Final Mail reply: `[bd-123] Completed` with summary and links

Mapping cheat-sheet

- **Mail `thread_id`** ↔ `bd-###`
- **Mail subject**: `[bd-###] …`
- **File reservation `reason`**: `bd-###`
- **Commit messages (optional)**: include `bd-###` for traceability

Event mirroring (optional automation)

- On `bd update --status blocked`, send a high-importance Mail message in thread `bd-###` describing the blocker.
- On Mail "ACK overdue" for a critical decision, add a Beads label (e.g., `needs-ack`) or bump priority to surface it in `bd ready`.

Pitfalls to avoid

- Don't create or manage tasks in Mail; treat Beads as the single task queue.
- Always include `bd-###` in message `thread_id` to avoid ID drift across tools.

### ast-grep vs ripgrep (quick guidance)

**Use `ast-grep` when structure matters.** It parses code and matches AST nodes, so results ignore comments/strings, understand syntax, and can **safely rewrite** code.

- Refactors/codemods: rename APIs, change import forms, rewrite call sites or variable kinds.
- Policy checks: enforce patterns across a repo (`scan` with rules + `test`).
- Editor/automation: LSP mode; `--json` output for tooling.

**Use `ripgrep` when text is enough.** It’s the fastest way to grep literals/regex across files.

- Recon: find strings, TODOs, log lines, config values, or non‑code assets.
- Pre-filter: narrow candidate files before a precise pass.

**Rule of thumb**

- Need correctness over speed, or you’ll **apply changes** → start with `ast-grep`.
- Need raw speed or you’re just **hunting text** → start with `rg`.
- Often combine: `rg` to shortlist files, then `ast-grep` to match/modify with precision.

**Snippets**

Find structured code (ignores comments/strings):

```bash
ast-grep run -l TypeScript -p 'import $X from "$P"'
```

Codemod (only real `var` declarations become `let`):

```bash
ast-grep run -l JavaScript -p 'var $A = $B' -r 'let $A = $B' -U
```

Quick textual hunt:

```bash
rg -n 'console\.log\(' -t js
```

Combine speed + precision:

```bash
rg -l -t ts 'useQuery\(' | xargs ast-grep run -l TypeScript -p 'useQuery($A)' -r 'useSuspenseQuery($A)' -U
```

**Mental model**

- Unit of match: `ast-grep` = node; `rg` = line.

- False positives: `ast-grep` low; `rg` depends on your regex.
- Rewrites: `ast-grep` first-class; `rg` requires ad‑hoc sed/awk and risks collateral edits.
