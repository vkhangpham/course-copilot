"""Generate quiz questions from the world model at runtime."""

from __future__ import annotations

from pathlib import Path
from typing import List

from ccopilot.core.validation import strict_validation

from .student_qa import QuizQuestion


def generate_quiz_questions(
    dataset_dir: Path,
    *,
    limit: int | None = None,
) -> List[QuizQuestion]:
    """Create quiz questions derived from concepts.yaml.

    Parameters
    ----------
    dataset_dir:
        Root directory of the handcrafted dataset bundle.
    limit:
        Optional maximum number of questions to emit.
    """

    concepts_path = (Path(dataset_dir) / "concepts.yaml").expanduser().resolve()
    result = strict_validation.validate_yaml_file(concepts_path)
    payload = result.data or {}
    concepts = payload.get("concepts") or {}
    if not isinstance(concepts, dict):
        raise ValueError("concepts.yaml must contain a 'concepts' mapping")

    items: List[QuizQuestion] = []
    for concept_id in sorted(concepts.keys()):
        data = concepts[concept_id] or {}
        name = data.get("name") or concept_id.replace("_", " ").title()
        summary = data.get("summary") or "Provide a concise explanation."
        prompt = f"Explain {name}."
        question = QuizQuestion(
            id=f"runtime-{concept_id}",
            prompt=prompt,
            answer_sketch=summary,
            learning_objectives=[concept_id],
            difficulty=data.get("difficulty", "medium"),
        )
        items.append(question)
        if limit is not None and len(items) >= limit:
            break

    if not items:
        raise ValueError("No concepts available for runtime quiz generation")
    return items
