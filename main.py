"""Convenience entry point for running the CourseGen CLI."""

from apps.orchestrator.run_poc import main as run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli())
