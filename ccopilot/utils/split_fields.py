"""Utility helpers shared across CLI and orchestrator modules."""

from __future__ import annotations

from collections.abc import Sequence
import re
from typing import Iterable, List

DEFAULT_DELIMITERS = r"[;,]"


def split_fields(value: str | Sequence[str] | None, *, delimiters: str = DEFAULT_DELIMITERS) -> List[str]:
    """Split a CSV-like field into trimmed tokens.

    Works for strings (splitting on the provided delimiters) or sequences (recursively splits
    each entry). Returns an empty list when the input is falsy.
    """

    if not value:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        tokens: List[str] = []
        for item in value:
            tokens.extend(split_fields(item, delimiters=delimiters))
        return tokens
    text = str(value)
    if not text:
        return []
    raw_tokens = re.split(delimiters, text)
    return [token.strip() for token in raw_tokens if token.strip()]
