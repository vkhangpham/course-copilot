# Plan – ccopilot-4gcs (dataset highlight provenance)

## Goal
Teach the portal backend to infer/propagate a dataset highlight source whenever the manifest omits it so the UI still shows provenance badges for ablated runs.

## Steps
1. Reproduce the portal responses when `highlight_source` is missing (manifest lacks the field) and confirm how `/runs` + `/runs/{id}` currently render provenance.
2. Update `apps/portal_backend/main.py` to derive a fallback highlight source (dataset vs world_model) using manifest fields like `world_model_highlights`, `ablations.use_world_model`, and `world_model_store_exists`, and thread that through both RunList/RunDetail responses.
3. Add regression coverage in `tests/test_portal_backend.py` covering manifests without `highlight_source` to ensure the derived label is stable.

## Progress
- 2025-11-13 05:01Z – Claimed bead, alerted PurpleMountain via Agent Mail, and drafted plan above. Inspecting teacher orchestrator next.
- 2025-11-13 05:03Z – Noticed teacher.py already modified locally (likely by PurpleMountain) to set `fallback_label="dataset"`; released reservations and refocused on the portal-driven fallback described in the updated bead notes.
- 2025-11-13 05:08Z – Added fallback heuristics to `_derive_highlight_source` (portal backend) and introduced a regression test covering manifests that omit `highlight_source` + `ablations`, relying solely on the store-exists flag.
