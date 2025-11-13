# Plan · ccopilot-o9q3 – Portal run list ablation flags

## Context
- Run detail already shows per-subsystem ablation state, but the run list only surfaces highlight source + scores.
- Current `AblationBadges` component renders badges *only* when subsystems are disabled, so you can’t tell at a glance whether a run used the world model/recursion/students unless an ablation was active.

## Steps
1. **API types** – confirm `RunListItem` exposes the `ablations` dict (settings already emit it) so the frontend can rely on a typed shape.
2. **UI update** – tweak `frontend/components/run-history.tsx` so ablation badges show all three subsystem states (using concise WM/ST/RC chips) with success/destructive colors.
3. **Verification** – run `npm run lint` within `frontend/` to ensure the TypeScript + ESLint checks pass.
