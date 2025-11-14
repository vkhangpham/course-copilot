# Plan – ccopilot-7ec (Typer validate-handcrafted command fails when run via entry point)

## Goal
The Typer CLI works via `python scripts/validate_handcrafted.py ...`, but the console script `validate-handcrafted` isn’t registered in `pyproject.toml`, so the entry point fails in installs/venvs. Wire up the entry point (setuptools console script), verify the command resolves Typer correctly, and add a smoke test.

## Steps
1. Update `pyproject.toml` (or setup entry) to expose `validate-handcrafted = scripts.validate_handcrafted:app`.
2. Add a lightweight test (maybe using `python -m scripts.validate_handcrafted`) to ensure the module can be invoked via console, or cover via docs + manual check.
3. Reinstall editable package to confirm `validate-handcrafted --help` works.
4. Update plan + Agent Mail.

## Progress
- 2025-11-13 01:40Z – Verified `pyproject.toml` already declares the `validate-handcrafted` console script and `python -m scripts.validate_handcrafted --help` works as expected; no change required.
