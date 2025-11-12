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

    def __init__(self) -> None:
        self._tools: Dict[str, ToolBinding] = {}
        self._programs: Dict[str, list[str]] = {}
        self._program_factories: Dict[str, Callable[[], object]] = {}

    def register_tool(self, binding: ToolBinding) -> None:
        if binding.name in self._tools:
            raise ValueError(f"Tool {binding.name} already registered")
        self._tools[binding.name] = binding

    def register_program(
        self,
        name: str,
        tool_names: Iterable[str],
        *,
        factory: Callable[[], object] | None = None,
    ) -> None:
        missing = [tool for tool in tool_names if tool not in self._tools]
        if missing:
            raise ValueError(f"Cannot register program {name}; missing tools {missing}")
        self._programs[name] = list(tool_names)
        if factory is not None:
            self._program_factories[name] = factory

    def describe(self) -> Mapping[str, Mapping[str, object] | list[str]]:
        return {
            "tools": {name: binding.description for name, binding in self._tools.items()},
            "programs": self._programs,
            "program_factories": sorted(self._program_factories.keys()),
        }

    def get_tool(self, name: str) -> ToolBinding:
        return self._tools[name]

    def build_program(self, name: str) -> object:
        factory = self._program_factories.get(name)
        if factory is None:
            raise KeyError(f"No factory registered for program {name}")
        return factory()
