# Plan – ccopilot-il2x (Run history should only show ablation badges when disabled)

## Goal
Run history currently shows "WM/ST/RC: On" badges even when everything is enabled, creating noise. Update the component to only render badges when a subsystem is disabled so alerts stand out.

## Steps
1. Adjust `frontend/components/run-history.tsx` `AblationBadges` logic to hide badges for enabled flags (or show a muted state), keeping accessible tooltips.
2. Update/extend any relevant Jest/React tests if they exist (none currently, so rely on manual visual diff + lint).
3. Communicate via Agent Mail + close bead.

## Progress
- 2025-11-13 00:31Z – Drafted plan.
- 2025-11-13 00:33Z – Updated RunHistory to only render badges for disabled flags; `pnpm lint` passes.
