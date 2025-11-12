# Plan – ccopilot-2g9 (Docs should mention wm-inspect auto-detects store)

## Goal
We recently anchored `wm-inspect` to the repo root, so users no longer need to pass `--store outputs/world_model/state.sqlite`. README and `docs/WORLD_MODEL_TOOLING.md` still show the flag everywhere. Update the docs to explain the new default (mention the env var override) and simplify the sample commands.

## Steps
1. Update README “World-Model Tooling” section to note that `wm-inspect` auto-detects the store and that `--store` is only needed for custom paths.
2. Update `docs/WORLD_MODEL_TOOLING.md` command table + troubleshooting tips with the same info.
3. Run `rg`/`markdownlint` spot-checks if needed; no tests required.
4. Update plan + send Agent Mail.

## Progress
- 2025-11-12 11:45Z – GreenBear opened ccopilot-2g9, reserved README/docs files, and is updating the wm-inspect sections.
- 2025-11-12 11:47Z – README + WORLD_MODEL_TOOLING now explain the auto-detected wm-inspect store and only mention `--store` for overrides.
