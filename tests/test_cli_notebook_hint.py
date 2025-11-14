from __future__ import annotations

import io
from contextlib import redirect_stdout
from types import SimpleNamespace

from ccopilot.cli.run_poc import _print_notebook_hint


def test_notebook_hint_reports_section_errors() -> None:
    artifacts = SimpleNamespace(
        notebook_exports=[
            {
                "kind": "section_error",
                "section": "course_plan",
                "response": {
                    "status": "error",
                    "reason": "validation_failure",
                    "error": "File missing",
                },
            }
        ],
        notebook_export_summary={"total": 1, "success": 0, "errors": 1},
    )
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        _print_notebook_hint(artifacts)

    text = buffer.getvalue()
    assert "[notebook] export unavailable" in text
    assert "status=error" in text
    assert "reason=validation_failure" in text


def test_notebook_hint_lists_failure_counts_when_partial_success() -> None:
    artifacts = SimpleNamespace(
        notebook_exports=[
            {
                "title": "Plan",
                "response": {"status": "ok", "notebook": "slug", "note_id": "slug-001"},
            },
            {
                "title": "Lecture",
                "response": {"status": "error", "error": "broken markdown"},
            },
        ],
        notebook_export_summary={"total": 2, "success": 1, "errors": 1},
    )
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        _print_notebook_hint(artifacts)

    text = buffer.getvalue()
    assert "[notebook] exported 1/2 sections" in text
    assert "1 error" in text
