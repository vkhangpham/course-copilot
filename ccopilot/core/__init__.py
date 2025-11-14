"""
Foundational configuration and logging utilities for the CourseGen PoC.

These modules are designed so higher-level orchestrators (run_poc, eval loop)
can depend on them without needing the rest of the scaffolded directories yet.
"""

from .ablation import AblationConfig, parse_ablation_flag
from .config import CourseConstraints, NotebookConfig, PipelineConfig, load_course_constraints
from .provenance import ProvenanceEvent, ProvenanceLogger

__all__ = [
    "AblationConfig",
    "CourseConstraints",
    "NotebookConfig",
    "PipelineConfig",
    "ProvenanceEvent",
    "ProvenanceLogger",
    "load_course_constraints",
    "parse_ablation_flag",
]
