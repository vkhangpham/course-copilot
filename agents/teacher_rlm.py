"""Wrapper around the Recursive Language Model (RLM) REPL."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict

from rich.console import Console


@dataclass
class TeacherRLM:
    """High-level façade that will talk to vendor/rlm implementation."""

    repl_factory: Callable[..., Any]
    tool_namespace: Dict[str, Callable[..., Any]] = field(default_factory=dict)
    console: Console = field(default_factory=Console)

    def bootstrap(self) -> None:
        """Load the RLM REPL and inject the tool namespace."""

        self.console.log("[teacher] Bootstrap RLM REPL (placeholder)")
        self._repl = self.repl_factory()
        for name, func in self.tool_namespace.items():
            setattr(self._repl, name, func)
        self.console.log(
            f"[teacher] Injected {len(self.tool_namespace)} tools into the REPL namespace"
        )

    def run(self, prompt_path: Path) -> dict[str, Any]:
        """Execute the teacher loop using the provided seed prompt."""

        if not hasattr(self, "_repl"):
            raise RuntimeError("TeacherRLM.bootstrap must be called before run().")
        prompt = prompt_path.read_text()
        self.console.log(f"[teacher] Starting loop with prompt file {prompt_path}")
        # Placeholder return; later this will return structured artifacts
        return {"prompt": prompt, "status": "not_implemented"}
