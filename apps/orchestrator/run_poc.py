"""Legacy-compatible CLI shim that delegates to ccopilot.cli.run_poc."""

from __future__ import annotations

from typing import List

from ccopilot.cli.run_poc import build_parser, main as _cli_main

__all__ = ["build_parser", "main"]


def main(argv: List[str] | None = None) -> int:
    """Invoke the canonical CLI implementation from ccopilot.cli.run_poc."""

    return _cli_main(argv)


if __name__ == "__main__":  # pragma: no cover - script entry point
    raise SystemExit(main())
