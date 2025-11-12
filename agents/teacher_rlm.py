"""Wrapper around the Recursive Language Model (RLM) REPL."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, MutableMapping, Optional, Sequence

from rich.console import Console


class TeacherRLMUnavailable(RuntimeError):
    """Raised when the vendor REPL cannot be instantiated."""


@dataclass
class TeacherRLMTask:
    """Declarative instruction that the teacher loop should execute."""

    kind: str
    target: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeacherActionRecord:
    """Structured trace entry captured during a teacher loop run."""

    action: str
    target: str
    payload: Dict[str, Any]
    result: Any | None


@dataclass
class TeacherRLMRun:
    """Return payload describing an RLM invocation (real or simulated)."""

    mode: str
    prompt_path: Path
    actions: List[TeacherActionRecord]
    summary: str


@dataclass
class TeacherRLM:
    """High-level façade that will talk to vendor/rlm implementation."""

    repl_factory: Callable[[], Any] | None = None
    tool_namespace: Dict[str, Callable[..., Any]] = field(default_factory=dict)
    console: Console = field(default_factory=Console)

    def bootstrap(self) -> None:
        """Load the RLM REPL and inject the tool namespace."""

        if hasattr(self, "_bootstrapped"):
            return

        self.console.log("[teacher] Bootstrapping RLM environment")
        repl = self._resolve_repl()
        for name, func in self.tool_namespace.items():
            setattr(repl, name, func)
        self._repl = repl
        self._bootstrapped = True
        self.console.log(
            f"[teacher] Injected {len(self.tool_namespace)} hooks into the REPL namespace"
        )

    def register_hook(self, name: str, func: Callable[..., Any]) -> None:
        """Expose a Python helper to the eventual REPL namespace."""

        self.tool_namespace[name] = func
        if hasattr(self, "_repl"):
            setattr(self._repl, name, func)

    def run(
        self,
        *,
        prompt_path: Path,
        context: Dict[str, Any] | None = None,
        tasks: Sequence[TeacherRLMTask] | None = None,
        query: Optional[str] = None,
    ) -> TeacherRLMRun:
        """Execute the teacher loop using the provided seed prompt."""

        self.bootstrap()
        prompt_text = prompt_path.read_text(encoding="utf-8")
        self.console.log(
            "[teacher] Starting loop",
            extra={"prompt": str(prompt_path), "tasks": len(tasks or [])},
        )
        try:
            if hasattr(self, "_repl") and hasattr(self._repl, "completion"):
                # TODO: invoke vendor RLM once the OpenAI plumbing is configured.
                # For now we intentionally fall back to the deterministic simulator
                # so tests can run offline.
                raise NotImplementedError("Vendor RLM execution not wired yet")
        except Exception as exc:  # pragma: no cover - guardrail
            self.console.log(
                "[teacher] Falling back to deterministic simulation",
                style="yellow",
                extra={"reason": str(exc)},
            )

        actions = self._simulate_run(tasks or [], prompt_text)
        summary = "; ".join(f"{a.action}:{a.target}" for a in actions) or "no-actions"
        return TeacherRLMRun(
            mode="simulation",
            prompt_path=prompt_path,
            actions=actions,
            summary=summary,
        )

    # ------------------------------------------------------------------

    def _resolve_repl(self) -> Any:
        if self.repl_factory is not None:
            return self.repl_factory()

        try:
            import importlib
            import sys

            vendor_path = self._vendor_rlm_path()
            if vendor_path.exists():
                vendor_str = str(vendor_path)
                if vendor_str not in sys.path:
                    sys.path.append(vendor_str)
            module = importlib.import_module("rlm.rlm_repl")
            return getattr(module, "RLM_REPL")()
        except Exception as exc:  # pragma: no cover - defensive
            self.console.log(
                "[teacher] Vendor RLM unavailable; using stub",
                style="yellow",
                extra={"reason": str(exc)},
            )

            class _StubRLM:
                def completion(self, *_args, **_kwargs):
                    raise NotImplementedError("Stub RLM cannot complete prompts")

            return _StubRLM()

    def _vendor_rlm_path(self) -> Path:
        """Return the directory that should contain the vendor RLM package."""

        override = os.environ.get("COURSEGEN_VENDOR_RLM_PATH")
        if override:
            return Path(override).expanduser()
        repo_root = Path(__file__).resolve().parents[1]
        return repo_root / "vendor" / "rlm"

    def _simulate_run(
        self,
        tasks: Sequence[TeacherRLMTask],
        prompt_text: str,
    ) -> List[TeacherActionRecord]:
        records: List[TeacherActionRecord] = []
        namespace: MutableMapping[str, Callable[..., Any]] = self.tool_namespace
        for task in tasks:
            hook = namespace.get(task.kind)
            if hook is None:
                records.append(
                    TeacherActionRecord(
                        action=task.kind,
                        target=task.target,
                        payload=task.payload,
                        result={"status": "missing_hook"},
                    )
                )
                continue
            try:
                result = hook(task.target, **task.payload)
            except Exception as exc:  # pragma: no cover - guardrail
                result = {"status": "error", "detail": str(exc)}
            records.append(
                TeacherActionRecord(
                    action=task.kind,
                    target=task.target,
                    payload=task.payload,
                    result=result,
                )
            )

        # Always log a final summary entry so downstream provenance has context.
        summary_payload = {
            "prompt_preview": prompt_text.splitlines()[0:2],
            "step_count": len(records),
        }
        records.append(
            TeacherActionRecord(
                action="log_event",
                target="teacher_summary",
                payload=summary_payload,
                result=None,
            )
        )
        return records
