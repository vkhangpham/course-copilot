# Plan – ccopilot-8qj (Document world-model env override for CodeAct)

## Goal
After ccopilot-tc1, the CodeAct world-model tools now respect `COURSEGEN_REPO_ROOT`, but the docs still only mention the CLI (`wm-inspect`). Update the World-Model tooling guide so operators know CodeAct fetches follow the same env overrides.

## Steps
1. Edit `docs/WORLD_MODEL_TOOLING.md` to add a short note near the common commands section describing how CodeAct tools resolve `WORLD_MODEL_STORE`/`COURSEGEN_REPO_ROOT`.
2. Review related README blurb to ensure it doesn’t contradict the new behavior (optional if already accurate).
3. Save, skim for formatting, and reference the bead in history/Agent Mail.

## Progress
- 2025-11-13 01:53Z – Added CodeAct env note to `docs/WORLD_MODEL_TOOLING.md` beneath the common commands table; README already aligned.
