"""Registry that wires DSPy CodeAct signatures to pure tool implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping


@dataclass(frozen=True)
class ToolBinding:
    """Pair a callable with metadata so CodeAct can invoke it safely."""

    name: str
    signature: str
    handler: Callable[..., object]
    description: str


class CodeActRegistry:
    """Simple, explicit registry for all CodeAct programs and tools."""

    def __init__(self, *, dspy_handles: object | None = None) -> None:
        self._tools: Dict[str, ToolBinding] = {}
        self._programs: Dict[str, list[str]] = {}
        self._program_factories: Dict[str, Callable[[], object]] = {}
        self._dspy_handles = dspy_handles
        self._program_roles: Dict[str, str | None] = {}

    def register_tool(self, binding: ToolBinding) -> None:
        if binding.name in self._tools:
            raise ValueError(f"Tool {binding.name} already registered")
        self._tools[binding.name] = binding

    def register_program(
        self,
        name: str,
        tool_names: Iterable[str],
        *,
        factory: Callable[..., object] | None = None,
        default_lm_role: str | None = None,
    ) -> None:
        missing = [tool for tool in tool_names if tool not in self._tools]
        if missing:
            raise ValueError(f"Cannot register program {name}; missing tools {missing}")
        self._programs[name] = list(tool_names)
        if factory is not None:
            self._program_factories[name] = factory
        self._program_roles[name] = default_lm_role

    def describe(self) -> Mapping[str, Mapping[str, object] | list[str]]:
        return {
            "tools": {name: binding.description for name, binding in self._tools.items()},
            "programs": self._programs,
            "program_factories": sorted(self._program_factories.keys()),
        }

    def get_tool(self, name: str) -> ToolBinding:
        return self._tools[name]

    def build_program(
        self,
        name: str,
        *,
        allowed_tools: Iterable[str] | None = None,
        lm_handle: object | None = None,
        lm_role: str | None = None,
    ) -> object:
        factory = self._program_factories.get(name)
        if factory is None:
            raise KeyError(f"No factory registered for program {name}")

        tool_names = self._programs.get(name, [])
        if not tool_names:
            raise ValueError(f"Program {name} has no registered tools")
        selected = self._select_tools(tool_names, allowed_tools)
        tool_handlers = [self._tools[tool].handler for tool in selected]
        kwargs: dict[str, object] = {"tools": tool_handlers}
        role_hint = lm_role or self._program_roles.get(name)
        resolved_lm = lm_handle or self._resolve_lm_role(role_hint)
        if resolved_lm is not None:
            kwargs["lm"] = resolved_lm
        return factory(**kwargs)

    def _select_tools(
        self,
        default_tools: list[str],
        allowed_tools: Iterable[str] | None,
    ) -> list[str]:
        if allowed_tools is None:
            return list(default_tools)
        allowed = {tool for tool in allowed_tools}
        filtered = [tool for tool in default_tools if tool in allowed]
        if not filtered:
            raise ValueError("Allowed tool list does not include any of the program tools")
        return filtered

    def _resolve_lm_role(self, lm_role: str | None) -> object | None:
        if not lm_role or not self._dspy_handles:
            return None
        normalized = lm_role.strip().lower()
        if normalized in {"teacher", "instructor"}:
            return getattr(self._dspy_handles, "teacher", None)
        if normalized in {"ta", "teaching_assistant", "assistant"}:
            return getattr(self._dspy_handles, "ta", None)
        if normalized in {"student", "grader"}:
            return getattr(self._dspy_handles, "student", None)
        if normalized in {"coder", "code", "codex"}:
            return getattr(self._dspy_handles, "coder", getattr(self._dspy_handles, "ta", None))
        # Fall back to attribute lookup so custom roles (e.g., "critic") can be added later.
        if hasattr(self._dspy_handles, normalized):
            return getattr(self._dspy_handles, normalized)
        return None
