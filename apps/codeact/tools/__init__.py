"""Aggregate exports for CodeAct tool wrappers.

The DSPy CodeAct interpreter replays each tool's source via `inspect.getsource`,
so annotations referring to names such as ``Path`` will raise ``NameError``
unless the corresponding imports are re-evaluated in the sandbox. Rather than
forcing every interpreter to duplicate our module imports, we expose thin
annotation-free wrappers that simply delegate to the real implementations.
"""

from __future__ import annotations

import inspect
from functools import update_wrapper
from typing import Callable

from . import data as _data_tools
from . import open_notebook as _notebook_tools
from . import world_model as _world_model_tools


def _wrap_tool(func: Callable) -> Callable:
    """Return a zero-annotation proxy that forwards to ``func``."""

    signature = inspect.signature(func)

    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    update_wrapper(wrapper, func, assigned=("__name__", "__qualname__", "__doc__", "__module__"), updated=())
    wrapper.__annotations__ = {}
    wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=[param.replace(annotation=inspect._empty) for param in signature.parameters.values()],
        return_annotation=inspect._empty,
    )
    return wrapper


fetch_concepts = _wrap_tool(_world_model_tools.fetch_concepts)
search_events = _wrap_tool(_world_model_tools.search_events)
lookup_paper = _wrap_tool(_world_model_tools.lookup_paper)
record_claim = _wrap_tool(_world_model_tools.record_claim)
list_claims = _wrap_tool(_world_model_tools.list_claims)
list_relationships = _wrap_tool(_world_model_tools.list_relationships)
link_concepts = _wrap_tool(_world_model_tools.link_concepts)
append_timeline_event = _wrap_tool(_world_model_tools.append_timeline_event)
persist_outline = _wrap_tool(_world_model_tools.persist_outline)

load_dataset_asset = _wrap_tool(_data_tools.load_dataset_asset)
run_sql_query = _wrap_tool(_data_tools.run_sql_query)

push_notebook_section = _wrap_tool(_notebook_tools.push_notebook_section)


__all__ = [
    "fetch_concepts",
    "search_events",
    "lookup_paper",
    "record_claim",
    "list_claims",
    "list_relationships",
    "link_concepts",
    "append_timeline_event",
    "persist_outline",
    "load_dataset_asset",
    "run_sql_query",
    "push_notebook_section",
]
