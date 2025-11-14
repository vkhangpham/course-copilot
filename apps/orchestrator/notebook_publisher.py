"""Helpers for publishing CourseGen artifacts to Open Notebook."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from apps.codeact.tools.open_notebook import ensure_notebook_exists, push_notebook_section

_CITATION_PATTERN = re.compile(r"\[([^\]]+)\]")
_ZERO_WIDTH_PREFIXES = "\ufeff\u200b\u200c\u200d\u2060\u202a\u202b\u202c\u202d\u202e"


def _strip_zero_width_prefix(text: str) -> str:
    """Remove zero-width and BOM markers that break heading detection."""

    return text.lstrip(_ZERO_WIDTH_PREFIXES)


def _is_setext_underline(line: str) -> bool:
    stripped = _strip_zero_width_prefix(line.strip())
    if not stripped:
        return False
    unique_chars = set(stripped)
    return unique_chars.issubset({"=", "-"}) and len(stripped.replace(" ", "")) >= 1


def _extract_setext_heading(lines: List[str], underline: str) -> str | None:
    if not lines or not _is_setext_underline(underline):
        return None
    candidate = _strip_zero_width_prefix(lines[-1].strip())
    if not candidate:
        return None
    lines.pop()
    return candidate


@dataclass(slots=True)
class NotebookSectionInput:
    title: str
    path: Path | None = None
    content: str | None = None


class NotebookPublisher:
    """Thin wrapper that chunks markdown artifacts into Notebook sections."""

    def __init__(
        self,
        *,
        notebook_slug: str,
        api_base: str | None = None,
        api_key: str | None = None,
        auto_create: bool = True,
        notebook_description: str | None = None,
    ) -> None:
        self._slug = notebook_slug
        self._api_base = api_base
        self._api_key = api_key
        self._auto_create = auto_create
        self._preflight_description = notebook_description
        self._preflight_attempted = False

    def publish(self, sections: Sequence[NotebookSectionInput]) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        preflight_entry = self._ensure_notebook_preflight()
        if preflight_entry is not None:
            results.append(preflight_entry)
        for section in sections:
            markdown = self._resolve_markdown(section)
            if markdown is None:
                continue
            title = self._resolve_title(section, markdown)
            citations = _extract_citations(markdown)
            try:
                response = push_notebook_section(
                    notebook_slug=self._slug,
                    title=title,
                    content_md=markdown,
                    citations=citations,
                    api_base=self._api_base,
                    api_key=self._api_key,
                    auto_create=self._auto_create,
                )
            except ValueError as exc:
                results.append(
                    {
                        "title": title,
                        "path": str(section.path) if section.path else None,
                        "citations": citations,
                        "response": {"status": "skipped", "error": str(exc)},
                    }
                )
                continue
            except Exception as exc:  # pragma: no cover - defensive
                results.append(
                    {
                        "title": title,
                        "path": str(section.path) if section.path else None,
                        "citations": citations,
                        "response": {"status": "error", "error": str(exc)},
                    }
                )
                continue
            if isinstance(response, dict):
                response.setdefault("notebook", self._slug)
            results.append(
                {
                    "title": title,
                    "path": str(section.path) if section.path else None,
                    "citations": citations,
                    "response": response,
                }
            )
        return results

    def _ensure_notebook_preflight(self) -> Dict[str, object] | None:
        if self._preflight_attempted:
            return None
        self._preflight_attempted = True
        base_entry = {
            "kind": "preflight",
            "title": "notebook_preflight",
            "response": {},
        }
        if not self._auto_create:
            base_entry["response"] = {
                "status": "skipped",
                "reason": "auto_create_disabled",
            }
            return base_entry
        if not self._api_base:
            base_entry["response"] = {
                "status": "skipped",
                "reason": "missing_api_base",
            }
            return base_entry
        try:
            response = ensure_notebook_exists(
                notebook_slug=self._slug,
                api_base=self._api_base,
                api_key=self._api_key,
                description=self._preflight_description,
            )
        except ValueError as exc:
            base_entry["response"] = {
                "status": "skipped",
                "error": str(exc),
            }
        except Exception as exc:  # pragma: no cover - defensive
            base_entry["response"] = {
                "status": "error",
                "error": str(exc),
            }
        else:
            if isinstance(response, dict):
                response.setdefault("notebook", self._slug)
            base_entry["response"] = response
        return base_entry

    def _resolve_markdown(self, section: NotebookSectionInput) -> str | None:
        if section.content is not None:
            content = section.content.strip()
            return content if content else None
        if section.path is None:
            return None
        if not section.path.exists():
            return None
        return section.path.read_text(encoding="utf-8")

    def _resolve_title(self, section: NotebookSectionInput, markdown: str) -> str:
        if section.content is not None and section.title:
            return section.title
        fallback = section.title or "Notebook Section"
        return self._derive_title(markdown, fallback=fallback)

    @staticmethod
    def _derive_title(markdown: str, *, fallback: str) -> str:
        lines = markdown.splitlines()
        for idx, line in enumerate(lines):
            stripped = _strip_zero_width_prefix(line.strip())
            if stripped.startswith("#"):
                heading = _strip_zero_width_prefix(stripped.lstrip("# ").strip())
                if heading:
                    return heading
            if idx > 0 and _is_setext_underline(line):
                candidate = _strip_zero_width_prefix(lines[idx - 1].strip())
                if candidate:
                    return candidate
        return fallback


def _extract_citations(markdown: str) -> List[str]:
    raw_tokens = [match.group(1).strip() for match in _CITATION_PATTERN.finditer(markdown)]
    normalized: List[str] = []
    seen_lower: set[str] = set()
    for token in raw_tokens:
        cleaned = token.strip("`*_ ")
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen_lower:
            continue
        seen_lower.add(lowered)
        normalized.append(cleaned)
    return sorted(normalized, key=lambda value: value.lower())


def chunk_markdown_sections(markdown: str, fallback_title: str) -> List[tuple[str, str]]:
    """Split markdown text into sections based on heading boundaries.

    Returns a list of ``(title, content)`` tuples. When no headings are
    present, a single fallback section is returned.
    """

    sections: List[tuple[str, str]] = []
    current_title = fallback_title
    current_lines: List[str] = []

    def flush() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_title, content))

    lines = markdown.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        heading = _extract_heading(line)
        if not heading:
            heading = _extract_setext_heading(current_lines, line)
            if heading:
                # Setext underline should not appear in section body.
                idx += 1
                if current_lines:
                    flush()
                current_title = heading
                current_lines = []
                continue
        if heading:
            if current_lines:
                flush()
            current_title = heading
            current_lines = []
            idx += 1
            continue
        current_lines.append(line)
        idx += 1

    if current_lines:
        flush()

    if not sections:
        return [(fallback_title, markdown.strip())]
    return sections


def build_sections_from_markdown(
    path: Path,
    fallback_title: str,
    *,
    max_sections: int | None = None,
    min_lines: int = 2,
) -> List[NotebookSectionInput]:
    """Utility to build ``NotebookSectionInput`` instances from a markdown file."""

    if not path.exists():
        return []

    markdown = path.read_text(encoding="utf-8")
    sections: List[NotebookSectionInput] = []
    for title, content in chunk_markdown_sections(markdown, fallback_title):
        is_fallback_section = title == fallback_title
        line_count = sum(1 for line in content.splitlines() if line.strip())
        if line_count < min_lines:
            if line_count == 0 or is_fallback_section:
                continue
        sections.append(NotebookSectionInput(title=title, path=path, content=content))
        if max_sections is not None and len(sections) >= max_sections:
            break

    if not sections:
        sections.append(NotebookSectionInput(title=fallback_title, path=path))
    return sections


def _extract_heading(line: str) -> str | None:
    stripped = _strip_zero_width_prefix(line.strip())
    if not stripped.startswith("#"):
        return None
    heading = _strip_zero_width_prefix(stripped.lstrip("# ").strip())
    return heading or None


__all__ = [
    "NotebookPublisher",
    "NotebookSectionInput",
    "build_sections_from_markdown",
    "chunk_markdown_sections",
]
