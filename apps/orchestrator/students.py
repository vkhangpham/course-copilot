"""Lightweight simulated student graders used during the PoC phase."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import yaml


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
    """Deterministic grader that scores artifacts using simple heuristics."""

    def __init__(
        self,
        rubrics: Sequence[RubricDefinition],
        *,
        required_sources: Sequence[str] | None = None,
    ) -> None:
        self.rubrics = list(rubrics)
        self.required_sources = [src.lower() for src in (required_sources or [])]
        self._source_keywords = self._build_source_keyword_map(self.required_sources)

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        *,
        required_sources: Sequence[str] | None = None,
    ) -> "StudentGraderPool":
        if not path.exists():
            raise FileNotFoundError(f"Rubrics file {path} is missing")

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
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
                        float(payload["pass_threshold"])
                        if "pass_threshold" in payload and payload["pass_threshold"] is not None
                        else None
                    ),
                    checklist=[str(item) for item in checklist],
                )
            )

        return cls(rubrics, required_sources=required_sources)

    def evaluate(self, artifact_path: Path) -> Dict[str, object]:
        """Score a markdown artifact and return rubric-level results."""

        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact {artifact_path} does not exist")

        text = artifact_path.read_text(encoding="utf-8")
        lowered = text.lower()
        rubric_results = []

        for rubric in self.rubrics:
            score, details = self._score_rubric(rubric, lowered_text=lowered, raw_text=text)
            threshold = rubric.pass_threshold if rubric.pass_threshold is not None else 0.75
            rubric_results.append(
                {
                    "name": rubric.name,
                    "score": round(score, 3),
                    "passed": score >= threshold,
                    "threshold": threshold,
                    "details": details,
                }
            )

        overall = (
            round(sum(item["score"] for item in rubric_results) / len(rubric_results), 3)
            if rubric_results
            else 1.0
        )

        return {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "rubrics": rubric_results,
            "overall_score": overall,
            "rubric_count": len(rubric_results),
        }

    # ------------------------------------------------------------------
    # Internal helpers

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
        kw_list = list(keywords)
        hits = [kw for kw in kw_list if cls._keyword_present(text, kw)]
        return (bool(hits), hits[0] if hits else None)

    @classmethod
    def _require_count(
        cls,
        text: str,
        keywords: Iterable[str],
        *,
        min_hits: int,
    ) -> Tuple[bool, str | None]:
        kw_list = list(keywords)
        hits = [kw for kw in kw_list if cls._keyword_present(text, kw)]
        return (len(hits) >= min_hits, ", ".join(hits[:min_hits]) if hits else None)

    @classmethod
    def _default_keyword_check(cls, normalized_item: str, lowered_text: str) -> Tuple[bool, str | None]:
        tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_item) if len(token) >= 4]
        hits = [token for token in tokens if cls._keyword_present(lowered_text, token)]
        return (bool(hits), hits[0] if hits else None)

    def _check_required_sources(self, lowered_text: str) -> Tuple[bool, str | None]:
        if not self._source_keywords:
            return True, None

        missing = []
        hits = []
        for source_id, keywords in self._source_keywords.items():
            if any(self._keyword_present(lowered_text, keyword) for keyword in keywords):
                hits.append(source_id)
            else:
                missing.append(source_id)

        return (not missing, ", ".join(hits) if hits else None)

    @staticmethod
    def _detect_citations(raw_text: str) -> Tuple[bool, str | None]:
        patterns = [
            (re.compile(r"\((?:19|20)\d{2}\)"), "year"),
            (re.compile(r"\[[^\]]+\]"), "brackets"),
            (re.compile(r"https?://"), "url"),
        ]
        for pattern, label in patterns:
            if pattern.search(raw_text):
                return True, label
        return False, None

    @staticmethod
    def _build_source_keyword_map(sources: Sequence[str]) -> Dict[str, List[str]]:
        if not sources:
            return {}

        mapping: Dict[str, List[str]] = {}
        for source in sources:
            normalized = source.lower().strip()
            if not normalized:
                continue
            tokens = {
                normalized,
                normalized.replace("-", " "),
                normalized.replace("_", " "),
            }
            if "-" in normalized:
                tokens.add(normalized.split("-", 1)[0])
            if " " in normalized:
                tokens.add(normalized.replace(" ", ""))
            mapping[source] = sorted({token for token in tokens if token})
        return mapping
