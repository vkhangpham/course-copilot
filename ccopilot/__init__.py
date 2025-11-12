"""
Core package for CourseGen PoC helpers.

This module is intentionally lightweight so the package can be imported
before the broader scaffolding (apps/, data/, etc.) is in place.
"""

from importlib import metadata


def get_version() -> str:
    """Return the installed project version."""
    try:
        return metadata.version("ccopilot")
    except metadata.PackageNotFoundError:
        return "0.0.0"


__all__ = ["get_version"]
