"""Stubbed Teacher/TA orchestration that integrates with ccopilot.pipeline."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from apps.codeact.registry import CodeActRegistry
from apps.codeact.tools.world_model import fetch_concepts, lookup_paper, search_events
from ccopilot.core.provenance import ProvenanceEvent
from ccopilot.pipeline.context import PipelineContext
from .students import StudentGraderPool

LOGGER_NAME = "coursegen.orchestrator"


@dataclass(slots=True)
class PipelineArtifacts:
    course_plan: Path
    lecture: Path
    eval_report: Path
    provenance: Path
    manifest: Path


class Orchestrator:
    """Thin façade around the future Teacher/TA loop.

    For now this class emits placeholder artifacts so we can exercise the
    bootstrap → runtime path without having the full RLM stack in place.
    """

    def __init__(
        self,
        ctx: PipelineContext,
        codeact_registry: CodeActRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.ctx = ctx
        self.registry = codeact_registry
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    def run(
        self,
        *,
        dataset_summary: Dict[str, Any],
        world_model_store: Path,
        snapshot_exists: bool,
        codeact_registry: CodeActRegistry | None = None,
    ) -> PipelineArtifacts:
        if codeact_registry is not None:
            self.registry = codeact_registry
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_dir = self.ctx.paths.output_dir
        lecture_dir = output_dir / "lectures"
        eval_dir = self.ctx.paths.evaluations_dir
        prov_dir = self.ctx.paths.logs_dir
        manifest_dir = self.ctx.paths.artifacts_dir

        for path in (output_dir, lecture_dir, eval_dir, prov_dir, manifest_dir):
            path.mkdir(parents=True, exist_ok=True)

        world_model_highlights = self._collect_world_model_highlights(world_model_store)

        self.logger.info(
            "Running placeholder orchestrator",
            extra={
                "ablations": self.ctx.ablations.describe(),
                "dataset_summary": dataset_summary,
                "world_model_store": str(world_model_store),
                "world_model_exists": snapshot_exists,
            },
        )
        self.ctx.provenance.log(
            ProvenanceEvent(
                stage="bootstrap",
                message="Orchestrator started",
                agent="apps.orchestrator",
                payload={
                    "ablations": self.ctx.ablations.describe(),
                    "dataset_summary": dataset_summary,
                    "world_model_store": str(world_model_store),
                    "world_model_store_exists": snapshot_exists,
                    "codeact_programs": (
                        self.registry.describe()["programs"] if self.registry else {}
                    ),
                },
            )
        )

        course_plan = self._emit_course_plan(
            output_dir,
            dataset_summary,
            world_model_highlights,
        )
        self._log_stage(
            "plan_course",
            {"course_plan": str(course_plan)},
        )
        lecture = self._emit_placeholder_lecture(
            lecture_dir,
            dataset_summary,
            world_model_highlights,
        )
        self._log_stage(
            "draft_lecture",
            {"lecture": str(lecture)},
        )
        evaluation_payload = self._evaluate_artifacts(lecture)
        eval_report = self._emit_eval_report(eval_dir, ts, evaluation_payload)
        self._log_stage(
            "evaluate",
            {
                "eval_report": str(eval_report),
                "use_students": evaluation_payload.get("use_students"),
                "overall_score": evaluation_payload.get("overall_score"),
            },
        )
        provenance = self._emit_provenance_record(
            prov_dir / f"run-{ts}.jsonl",
            course_plan,
            lecture,
            dataset_summary,
            world_model_highlights,
        )
        manifest = self._emit_manifest(
            manifest_dir / f"run-{ts}-manifest.json",
            course_plan,
            lecture,
            eval_report,
            provenance,
            dataset_summary,
            world_model_store,
            snapshot_exists,
            evaluation_payload,
            world_model_highlights,
        )

        self.ctx.provenance.log(
            ProvenanceEvent(
                stage="complete",
                message="Placeholder run complete",
                agent="apps.orchestrator",
                payload={
                    "course_plan": str(course_plan),
                    "lecture": str(lecture),
                    "eval_report": str(eval_report),
                    "evaluation": evaluation_payload,
                    "world_model_highlights": world_model_highlights or {},
                },
            )
        )

        return PipelineArtifacts(
            course_plan=course_plan,
            lecture=lecture,
            eval_report=eval_report,
            provenance=provenance,
            manifest=manifest,
        )

    def _log_stage(self, stage_name: str, payload: Dict[str, Any]) -> None:
        self.ctx.provenance.log(
            ProvenanceEvent(
                stage=stage_name,
                message=f"Stage {stage_name} completed (placeholder)",
                agent="apps.orchestrator",
                payload=payload,
            )
        )

    # ------------------------------------------------------------------

    def _emit_course_plan(self, output_dir: Path, dataset_summary: Dict[str, Any]) -> Path:
        course = self.ctx.config.course
        plan_path = output_dir / "course_plan.md"
        with plan_path.open("w", encoding="utf-8") as handle:
            handle.write(f"# {course.title}\n\n")
            handle.write(f"**Duration:** {course.duration_weeks} weeks\n\n")
            handle.write("## Learning Objectives\n")
            for objective in course.learning_objectives:
                handle.write(f"- {objective}\n")
            handle.write("\n## Dataset Snapshot\n")
            handle.write(f"- Concepts: {dataset_summary['concept_count']}\n")
            handle.write(f"- Papers: {dataset_summary['paper_count']}\n")
            handle.write(f"- Timeline events: {dataset_summary['timeline_count']}\n")
            handle.write(f"- Quiz items: {dataset_summary['quiz_count']}\n")
            if dataset_summary.get("top_domains"):
                handle.write(
                    f"- Domains: {', '.join(dataset_summary['top_domains'])}\n"
                )
            handle.write("\n> Placeholder plan – replace once Teacher RLM is wired.\n")
        return plan_path

    def _emit_placeholder_lecture(
        self, lecture_dir: Path, dataset_summary: Dict[str, Any]
    ) -> Path:
        lecture_path = lecture_dir / "module_01.md"
        with lecture_path.open("w", encoding="utf-8") as handle:
            handle.write("# Module 1 · Foundations of Database Systems\n\n")
            handle.write(
                "This stub is generated while the TA CodeAct loop is under construction.\n"
            )
            handle.write("Each real run will include citations, examples, and student prompts.\n")
            focus = (dataset_summary.get("top_domains") or ["Database Systems"])[0]
            handle.write(f"\n_Current dataset focus: {focus}_\n")
            handle.write("\n## Learning Objectives & Assessments\n")
            handle.write("- Learning objective: Explain the relational model, SQL, and why normalization matters.\n")
            handle.write(
                "- Assessment strategy: short concept quizzes plus a transactional lab on locking and recovery.\n\n"
            )
            handle.write("## Concept Coverage\n")
            handle.write(
                "We revisit relational algebra and SQL before contrasting concurrency control mechanisms,"
            )
            handle.write(
                " recovery logs, and distributed systems such as Spanner and resilient NewSQL engines.\n\n"
            )
            handle.write("## Worked Example\n")
            handle.write(
                "Consider a banking workload: a transaction debits one account and credits another. "
            )
            handle.write(
                "We trace how two-phase locking prevents lost updates while recovery replays committed entries.\n\n"
            )
            handle.write("## Review Questions\n")
            handle.write(
                "1. Why does strict two-phase locking guarantee serializability?\n"
                "2. Which SQL query would expose a partial failure in the example above?\n"
            )
            handle.write("\n## Sources & Citations\n")
            handle.write(
                "- Codd (1970) formalized the relational model and relational algebra [`codd-1970`].\n"
            )
            handle.write(
                "- System R (1976) demonstrated cost-based SQL optimization and transactions [`system-r-1976`].\n"
            )
            handle.write(
                "- Postgres, ARIES, and Spanner extend these ideas to modern distributed databases.\n"
            )
        return lecture_path

    def _emit_eval_report(self, eval_dir: Path, ts: str, payload: Dict[str, Any]) -> Path:
        eval_path = eval_dir / f"run-{ts}.jsonl"
        record = {"timestamp": ts, **payload}
        with eval_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return eval_path

    def _emit_provenance_record(
        self,
        path: Path,
        course_plan: Path,
        lecture: Path,
        dataset_summary: Dict[str, Any],
    ) -> Path:
        record = {
            "stage": "placeholder",
            "message": "Artifacts emitted",
            "agent": "apps.orchestrator",
            "payload": {
                "course_plan": str(course_plan),
                "lecture": str(lecture),
                "world_model_enabled": self.ctx.ablations.use_world_model,
                "students_enabled": self.ctx.ablations.use_students,
                "dataset_summary": dataset_summary,
            },
        }
        with path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return path

    def _emit_manifest(
        self,
        path: Path,
        course_plan: Path,
        lecture: Path,
        eval_report: Path,
        provenance: Path,
        dataset_summary: Dict[str, Any],
        world_model_store: Path,
        snapshot_exists: bool,
        evaluation_payload: Dict[str, Any],
    ) -> Path:
        manifest: Dict[str, Any] = {
            "course_plan": str(course_plan),
            "lecture": str(lecture),
            "eval_report": str(eval_report),
            "provenance": str(provenance),
            "ablations": {
                "use_world_model": self.ctx.ablations.use_world_model,
                "use_students": self.ctx.ablations.use_students,
                "allow_recursion": self.ctx.ablations.allow_recursion,
            },
            "dataset_summary": dataset_summary,
            "world_model_store": str(world_model_store),
            "world_model_store_exists": snapshot_exists,
            "evaluation": evaluation_payload,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        return path

    def _evaluate_artifacts(self, lecture_path: Path) -> Dict[str, Any]:
        if not self.ctx.ablations.use_students:
            return {"use_students": False, "status": "students_disabled"}

        rubrics_path = self.ctx.config.evaluation.rubrics_path
        try:
            grader = StudentGraderPool.from_yaml(
                rubrics_path,
                required_sources=self.ctx.config.course.required_sources,
            )
        except FileNotFoundError:
            return {
                "use_students": False,
                "status": "missing_rubrics",
                "rubrics_path": str(rubrics_path),
            }
        except ValueError as exc:
            return {
                "use_students": False,
                "status": "invalid_rubrics",
                "error": str(exc),
                "rubrics_path": str(rubrics_path),
            }

        results = grader.evaluate(lecture_path)
        return {"use_students": True, **results, "rubrics_path": str(rubrics_path)}
