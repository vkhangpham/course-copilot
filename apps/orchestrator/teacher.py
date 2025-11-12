"""Teacher RLM scaffolding and orchestration loop placeholders."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .shared_state import SharedStateHandles


@dataclass
class OrchestratorConfig:
    """Subset of configuration values required to bootstrap the teacher loop."""

    course_constraints: Path
    concept_root: Path
    notebook_name: str
    ablation: Optional[str] = None


class TeacherOrchestrator:
    """Stub implementation that will be replaced in ccopilot-syy.

    This class focuses on wiring dependencies so later issues can implement the
    actual recursive agent behavior.
    """

    def __init__(self, shared_state: SharedStateHandles) -> None:
        self.shared_state = shared_state
        self.logger = logging.getLogger("coursegen.teacher")

    def run_coursegen(self, config: OrchestratorConfig) -> None:
        """Entry point invoked by the CLI.

        For scaffolding we only verify directories exist and log upcoming work.
        Future issues will flesh this out with the full RLM + CodeAct pipeline.
        """

        self.shared_state.ensure_dirs()
        self._log_run_context(config)
        raise NotImplementedError(
            "TeacherOrchestrator.run_coursegen will be implemented in ccopilot-syy."
        )

    def available_ablation_flags(self) -> Iterable[str]:
        """Documented ablation toggles from docs/PLAN.md."""

        return ("disable-rlm", "disable-students", "disable-world-model")

    def _log_run_context(self, config: OrchestratorConfig) -> None:
        self.logger.info(
            "Starting CourseGen run",
            extra={
                "concept_root": str(config.concept_root),
                "notebook": config.notebook_name,
                "ablation": config.ablation,
            },
        )
