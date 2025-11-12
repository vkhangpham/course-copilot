"""FastAPI portal backend for CourseGen artifacts."""

from .main import app  # re-export for uvicorn convenience

__all__ = ["app"]
