# Plan – ccopilot-62nb (Manifest should redact world_model_store path)

## Goal
Prevent RunDetail responses from leaking the absolute `world_model_store` path by adding it (and any other stray path fields) to the manifest sanitizer so only outputs-relative paths are returned.

## Steps
1. Confirm current RunDetail payload still includes the absolute sqlite path and identify any other path-like keys not yet sanitized.
2. Update `_sanitize_manifest_paths` + supporting helpers so `world_model_store` (and siblings) become outputs-relative.
3. Extend portal backend tests to assert the sanitized manifest reports `world_model_store` relative to outputs.
4. Run `pytest tests/test_portal_backend.py` and report via Agent Mail.

## Status
- 2025-11-13 04:05Z – Plan drafted; confirming manifest contents now.
