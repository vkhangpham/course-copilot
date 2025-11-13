# Plan – ccopilot-6alj (Expose science config in run detail)

## Goal
Show the full scientific evaluator config path on the run detail page so auditors don’t have to rely on the small hint in RunHistory.

## Steps
1. Update `RunDetailSection` to derive the science config path (from `detail.science_config_path` or manifest) and render it alongside other artifact info.
2. Keep UI accessible (monospace, wraps gracefully) and ensure server component builds cleanly.
3. Communicate updates + close the bead.

## Progress
- 2025-11-13 00:19Z – Drafted plan; implementation next.
- 2025-11-13 00:22Z – Added science config path to RunDetailSection artifacts panel; `pnpm lint` passes.
