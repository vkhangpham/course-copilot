"""Student graders used by the CourseGen orchestrator."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from ccopilot.core.validation import ValidationFailure, strict_validation

from .student_settings import students_llm_disabled

LOGGER = logging.getLogger(__name__)
DEFAULT_LLM_CHAR_BUDGET = int(os.getenv("COURSEGEN_STUDENT_LLM_CHAR_LIMIT", "6000"))


@dataclass(slots=True)
class RubricDefinition:
    """Represents a rubric entry loaded from `evals/rubrics.yaml`."""

    name: str
    description: str
    pass_threshold: float | None
    checklist: List[str]

    @property
    def normalized_name(self) -> str:
        return self.name.strip().lower()


class StudentGraderPool:
    """Grades artifacts via rubric definitions, using an LLM when available."""

    def __init__(
        self,
        rubrics: Sequence[RubricDefinition],
        *,
        required_sources: Sequence[str] | None = None,
        lm: Any | None = None,
        max_chars: int | None = None,
    ) -> None:
        self.rubrics = list(rubrics)
        self.required_sources = [src.lower() for src in (required_sources or [])]
        self.lm = lm
        self._max_chars = max_chars or DEFAULT_LLM_CHAR_BUDGET
        self._use_llm = bool(lm) and not students_llm_disabled()

    @property
    def uses_llm(self) -> bool:
        return self._use_llm

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        required_sources: Sequence[str] | None = None,
        lm: Any | None = None,
        max_chars: int | None = None,
    ) -> "StudentGraderPool":
        if not path.exists():
            raise FileNotFoundError(f"Rubrics file {path} is missing")

        try:
            data = strict_validation.validate_yaml_file(path).data or {}
        except ValidationFailure as exc:
            raise ValueError(f"Invalid rubrics file {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"Rubrics file {path} must define a mapping")

        rubrics: List[RubricDefinition] = []
        for name, payload in data.items():
            if not isinstance(payload, dict):
                continue
            checklist = payload.get("checklist") or []
            if not isinstance(checklist, list):
                checklist = [str(checklist)]
            rubrics.append(
                RubricDefinition(
                    name=name,
                    description=str(payload.get("description", "")),
                    pass_threshold=(
                        float(payload["pass_threshold"]) if "pass_threshold" in payload and payload["pass_threshold"] is not None else None
                    ),
                    checklist=[str(item) for item in checklist],
                )
            )

        return cls(rubrics, required_sources=required_sources, lm=lm, max_chars=max_chars)

    # ------------------------------------------------------------------

    def evaluate(self, artifact_path: Path) -> Dict[str, object]:
        """Score a markdown artifact and return rubric-level results."""

        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact {artifact_path} does not exist")

        text = artifact_path.read_text(encoding="utf-8")
        rubric_results = self._evaluate_with_llm(text) if self._use_llm else self._evaluate_with_heuristics(text)
        overall = round(sum(entry["score"] for entry in rubric_results) / len(rubric_results), 3) if rubric_results else 1.0

        engine = "llm" if self._use_llm else "heuristic"

        return {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "rubrics": rubric_results,
            "overall_score": overall,
            "rubric_count": len(rubric_results),
            "engine": engine,
        }

    # ------------------------------------------------------------------
    # LLM-enabled grading

    def _evaluate_with_llm(self, text: str) -> List[Dict[str, Any]]:
        excerpt = self._trim_text(text)
        entries: List[Dict[str, Any]] = []
        for rubric in self.rubrics:
            payload = self._grade_rubric_with_llm(rubric, excerpt)
            if payload is None:
                score, details = self._score_rubric(rubric, lowered_text=text.lower(), raw_text=text)
            else:
                details = self._details_from_lm_payload(rubric, payload)
                score = self._score_from_details(details, payload.get("overall_score"))
            threshold = rubric.pass_threshold if rubric.pass_threshold is not None else 0.75
            entries.append(
                {
                    "name": rubric.name,
                    "score": round(score, 3),
                    "passed": score >= threshold,
                    "threshold": threshold,
                    "details": details,
                }
            )
        return entries

    def _grade_rubric_with_llm(self, rubric: RubricDefinition, lecture_excerpt: str) -> Dict[str, Any] | None:
        if not self._use_llm:
            return None

        checklist = rubric.checklist or ["overall quality"]
        checklist_block = "\n".join(f"- {item}" for item in checklist)
        required_sources = ", ".join(self.required_sources) if self.required_sources else "none"
        prompt = dedent(
            f"""
        You are an expert teaching assistant who grades course materials.

        Rubric name: {rubric.name}
        Description: {rubric.description}
        Checklist:
        {checklist_block}

        Required canonical sources that must be cited explicitly: {required_sources}.

        Read the lecture excerpt between <lecture></lecture> and evaluate how well it satisfies
        the rubric. Cite short evidence from the lecture whenever possible.

        <lecture>
        {lecture_excerpt}
        </lecture>

        Respond with JSON using this schema:
        {{
          "overall_score": number between 0 and 1,
          "items": [
            {{"item": "checklist entry", "passed": true/false, "score": number between 0 and 1, "evidence": "short justification"}}
          ]
        }}

        Output JSON only.
        """
        ).strip()

        data = self._call_lm_json(prompt)
        return data

    def _details_from_lm_payload(self, rubric: RubricDefinition, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        details: List[Dict[str, Any]] = []
        for item in payload.get("items", []) or []:
            details.append(
                {
                    "item": item.get("item", "unspecified"),
                    "passed": bool(item.get("passed")),
                    "score": float(item.get("score", 1.0 if item.get("passed") else 0.0)),
                    "evidence": item.get("evidence"),
                }
            )
        if not details and rubric.checklist:
            default_score = float(payload.get("overall_score") or 0.0)
            for entry in rubric.checklist:
                details.append(
                    {
                        "item": entry,
                        "passed": default_score >= (rubric.pass_threshold or 0.75),
                        "score": default_score,
                        "evidence": None,
                    }
                )
        if not details:
            details.append({"item": rubric.name, "passed": False, "score": 0.0, "evidence": None})
        return details

    @staticmethod
    def _score_from_details(details: List[Dict[str, Any]], overall_hint: Any) -> float:
        explicit = [float(row.get("score")) for row in details if row.get("score") is not None]
        if explicit:
            return sum(explicit) / len(explicit)
        if details:
            return sum(1 for row in details if row.get("passed")) / len(details)
        if overall_hint is not None:
            try:
                return float(overall_hint)
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _call_lm_json(self, prompt: str) -> Dict[str, Any] | None:
        if not self._use_llm:
            return None
        try:
            raw = self.lm(prompt=prompt)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Student grader LM call failed: %s", exc)
            return None
        text = self._normalize_lm_output(raw)
        return self._extract_json(text)

    @staticmethod
    def _normalize_lm_output(raw: Any) -> str:
        if isinstance(raw, list):
            return "\n".join(str(part) for part in raw)
        return str(raw)

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any] | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None

    def _trim_text(self, text: str) -> str:
        if len(text) <= self._max_chars:
            return text
        return text[: self._max_chars] + "\n\n[Truncated for evaluation]"

    # ------------------------------------------------------------------
    # Heuristic fallback (legacy behaviour)

    def _evaluate_with_heuristics(self, text: str) -> List[Dict[str, Any]]:
        lowered = text.lower()
        results: List[Dict[str, Any]] = []
        for rubric in self.rubrics:
            score, details = self._score_rubric(rubric, lowered_text=lowered, raw_text=text)
            threshold = rubric.pass_threshold if rubric.pass_threshold is not None else 0.75
            results.append(
                {
                    "name": rubric.name,
                    "score": round(score, 3),
                    "passed": score >= threshold,
                    "threshold": threshold,
                    "details": details,
                }
            )
        return results

    def _score_rubric(
        self,
        rubric: RubricDefinition,
        *,
        lowered_text: str,
        raw_text: str,
    ) -> Tuple[float, List[Dict[str, object]]]:
        if not rubric.checklist:
            return 1.0, []

        detail_rows: List[Dict[str, object]] = []
        for item in rubric.checklist:
            normalized = item.strip().lower()
            if rubric.normalized_name == "coverage":
                passed, evidence = self._coverage_check(normalized, lowered_text)
            elif rubric.normalized_name == "grounding":
                passed, evidence = self._grounding_check(normalized, lowered_text, raw_text)
            elif rubric.normalized_name == "pedagogy":
                passed, evidence = self._pedagogy_check(normalized, lowered_text)
            else:
                passed, evidence = self._default_keyword_check(normalized, lowered_text)

            detail_rows.append({"item": item, "passed": passed, "evidence": evidence})

        score = sum(1 for row in detail_rows if row["passed"]) / len(detail_rows)
        return score, detail_rows

    # Coverage ---------------------------------------------------------

    def _coverage_check(self, normalized_item: str, lowered_text: str) -> Tuple[bool, str | None]:
        if "relational model" in normalized_item and "sql" in normalized_item:
            return self._require_all(lowered_text, ["relational", "sql"])
        if "transactions" in normalized_item or "concurrency" in normalized_item:
            return self._require_count(
                lowered_text,
                ["transaction", "transactions", "recovery", "concurrency", "locking"],
                min_hits=2,
            )
        if "distributed" in normalized_item or "modern databases" in normalized_item:
            return self._require_any(
                lowered_text,
                [
                    "distributed",
                    "spanner",
                    "aurora",
                    "newsql",
                    "modern database",
                ],
            )
        return self._default_keyword_check(normalized_item, lowered_text)

    # Grounding --------------------------------------------------------

    def _grounding_check(
        self,
        normalized_item: str,
        lowered_text: str,
        raw_text: str,
    ) -> Tuple[bool, str | None]:
        if "learning objective" in normalized_item or "primary source" in normalized_item:
            return self._check_required_sources(lowered_text)
        citation_tokens = ("cite", "citation", "citations", "reference", "references", "papers")
        if any(token in normalized_item for token in citation_tokens):
            return self._detect_citations(raw_text)
        return self._default_keyword_check(normalized_item, lowered_text)

    # Pedagogy ---------------------------------------------------------

    def _pedagogy_check(self, normalized_item: str, lowered_text: str) -> Tuple[bool, str | None]:
        if "learning objectives" in normalized_item and "assessments" in normalized_item:
            return self._require_all(lowered_text, ["learning objective", "assessment"])
        if "worked examples" in normalized_item or "review questions" in normalized_item:
            return self._require_all(lowered_text, ["example", "question"])
        return self._default_keyword_check(normalized_item, lowered_text)

    # Shared primitives ------------------------------------------------

    @staticmethod
    def _keyword_present(text: str, keyword: str) -> bool:
        if not keyword:
            return False
        pattern = rf"\b{re.escape(keyword)}\b"
        return re.search(pattern, text) is not None

    @classmethod
    def _require_all(cls, text: str, keywords: Iterable[str]) -> Tuple[bool, str | None]:
        kw_list = list(keywords)
        matches = [kw for kw in kw_list if cls._keyword_present(text, kw)]
        return (len(matches) == len(kw_list), ", ".join(matches) if matches else None)

    @classmethod
    def _require_any(cls, text: str, keywords: Iterable[str]) -> Tuple[bool, str | None]:
        matches = [kw for kw in keywords if cls._keyword_present(text, kw)]
        return (bool(matches), matches[0] if matches else None)

    @classmethod
    def _require_count(cls, text: str, keywords: Iterable[str], *, min_hits: int) -> Tuple[bool, str | None]:
        matches = [kw for kw in keywords if cls._keyword_present(text, kw)]
        return (len(matches) >= min_hits, ", ".join(matches) if matches else None)

    @classmethod
    def _default_keyword_check(cls, normalized_item: str, text: str) -> Tuple[bool, str | None]:
        tokens = [token.strip() for token in normalized_item.split(" ") if token.strip()]
        if not tokens:
            return False, None
        matches = [token for token in tokens if cls._keyword_present(text, token)]
        return (bool(matches), matches[0] if matches else None)

    def _check_required_sources(self, text: str) -> Tuple[bool, str | None]:
        if not self.required_sources:
            return True, None
        matches = [source for source in self.required_sources if source.lower() in text]
        return len(matches) == len(self.required_sources), ", ".join(matches) if matches else None

    def _detect_citations(self, raw_text: str) -> Tuple[bool, str | None]:
        if not self.required_sources:
            return True, None
        lowered = raw_text.lower()
        matches = [source for source in self.required_sources if source.lower() in lowered]
        return bool(matches), ", ".join(matches) if matches else None


__all__ = ["StudentGraderPool", "RubricDefinition"]
