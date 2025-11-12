"""Teacher orchestrator that drives the CourseGen CodeAct programs."""
from __future__ import annotations

import json
import logging
import inspect
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from agents.ta_roles import DEFAULT_ROLES, TARoleSpec
from agents.teacher_rlm import (
    TeacherActionRecord,
    TeacherRLM,
    TeacherRLMRun,
    TeacherRLMTask,
    TeacherRLMUnavailable,
)
from apps.codeact.registry import CodeActRegistry
from apps.codeact.tools.world_model import fetch_concepts, lookup_paper, search_events
from apps.orchestrator.notebook_publisher import (
    NotebookPublisher,
    NotebookSectionInput,
    build_sections_from_markdown,
)
from apps.orchestrator.student_loop import MutationReason, StudentLoopConfig, StudentLoopRunner
from apps.orchestrator.student_qa import StudentQuizEvaluator
from apps.orchestrator.ta_roles.exercise_author import ExerciseAuthor
from apps.orchestrator.ta_roles.explainer import Explainer
from apps.orchestrator.ta_roles.reading_curator import ReadingCurator
from apps.orchestrator.ta_roles.syllabus_designer import SyllabusDesigner
from apps.orchestrator.ta_roles.timeline_synthesizer import TimelineSynthesizer
from ccopilot.core.provenance import ProvenanceEvent
from ccopilot.pipeline.context import PipelineContext

from .shared_state import SharedStateHandles
from .students import StudentGraderPool

LOGGER_NAME = "coursegen.orchestrator"
WORLD_MODEL_PROGRAMS = {"PlanCourse", "DraftLectureSection", "EnforceCitations"}


@dataclass(slots=True)
class TeacherArtifacts:
    course_plan: Path
    lecture: Path
    eval_report: Path
    provenance: Path
    manifest: Path
    highlights: Path | None = None
    teacher_trace: Path | None = None
    notebook_exports: List[Dict[str, Any]] | None = None
    notebook_export_summary: Dict[str, Any] | None = None


class TeacherOrchestrator:
    """Teacher/TA orchestration surface that emits run artifacts."""

    def __init__(
        self,
        ctx: PipelineContext,
        *,
        shared_state: SharedStateHandles | None = None,
        codeact_registry: CodeActRegistry | None = None,
        teacher_rlm: TeacherRLM | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.ctx = ctx
        self.registry = codeact_registry
        self.shared_state = shared_state or SharedStateHandles(
            concept_root=ctx.config.world_model.dataset_dir,
            artifact_root=ctx.paths.output_dir,
            eval_root=ctx.paths.evaluations_dir,
        )
        self.teacher_rlm = teacher_rlm or TeacherRLM()
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self._teacher_cache: Dict[str, Any] = {}
        self.ta_roles: Dict[str, TARoleSpec] = {role.name: role for role in DEFAULT_ROLES}

    def run_coursegen(
        self,
        *,
        dataset_summary: Dict[str, Any],
        world_model_store: Path,
        snapshot_exists: bool,
        codeact_registry: CodeActRegistry | None = None,
    ) -> TeacherArtifacts:
        if codeact_registry is not None:
            self.registry = codeact_registry
        self.shared_state.ensure_dirs()
        self._teacher_cache = {}
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output_dir = self.ctx.paths.output_dir
        lecture_dir = output_dir / "lectures"
        eval_dir = self.ctx.paths.evaluations_dir
        prov_dir = self.ctx.paths.logs_dir
        manifest_dir = self.ctx.paths.artifacts_dir

        for path in (output_dir, lecture_dir, eval_dir, prov_dir, manifest_dir):
            path.mkdir(parents=True, exist_ok=True)

        if self.ctx.ablations.use_world_model:
            world_model_highlights = self._collect_world_model_highlights(world_model_store)
            manifest_world_model_highlights = world_model_highlights
            highlight_artifact = self._emit_world_model_highlights_artifact(
                manifest_dir,
                ts,
                world_model_highlights,
                dataset_summary,
            )
        else:
            world_model_highlights = self._collect_dataset_highlights()
            manifest_world_model_highlights = None
            highlight_artifact = None
            self.logger.info("World-model ablation enabled; skipping persisted highlight snapshot.")

        teacher_trace: Path | None = None
        if self.ctx.ablations.allow_recursion:
            teacher_trace = self._run_teacher_loop(
                ts,
                dataset_summary=dataset_summary,
                world_model_highlights=world_model_highlights,
            )
        else:
            self.logger.info("Recursion disabled; skipping teacher RLM loop.")

        self.logger.info(
            "Running teacher orchestrator",
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
                message="Teacher orchestrator started",
                agent="apps.orchestrator.teacher",
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
        lecture = self._emit_lecture(
            lecture_dir,
            dataset_summary,
            world_model_highlights,
        )
        self._log_stage(
            "draft_lecture",
            {"lecture": str(lecture)},
        )
        evaluation_payload = self._evaluate_artifacts(lecture, world_model_highlights)
        eval_report = self._emit_eval_report(eval_dir, ts, evaluation_payload)
        self._log_stage(
            "evaluate",
            {
                "eval_report": str(eval_report),
                "use_students": evaluation_payload.get("use_students"),
                "overall_score": evaluation_payload.get("overall_score"),
            },
        )
        notebook_exports: List[Dict[str, Any]] | None = None
        if self._notebook_exports_enabled():
            notebook_exports = self._publish_notebook_sections(course_plan, lecture)
        elif getattr(self.ctx.config, "notebook", None):
            notebook_exports = [self._notebook_placeholder(reason=self._notebook_skip_reason())]
        if notebook_exports is None and getattr(self.ctx.config, "notebook", None):
            notebook_exports = [self._notebook_placeholder(reason="notebook_disabled")]
        notebook_export_summary = self._summarize_notebook_exports(notebook_exports)
        provenance = self._emit_provenance_record(
            prov_dir / f"run-{ts}.jsonl",
            course_plan,
            lecture,
            dataset_summary,
            manifest_world_model_highlights,
            notebook_export_summary,
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
            manifest_world_model_highlights,
            highlight_artifact,
            teacher_trace,
            notebook_exports,
            notebook_export_summary,
        )

        self.ctx.provenance.log(
            ProvenanceEvent(
                stage="complete",
                message="Teacher orchestrator run complete",
                agent="apps.orchestrator.teacher",
                payload={
                    "course_plan": str(course_plan),
                    "lecture": str(lecture),
                    "eval_report": str(eval_report),
                    "evaluation": evaluation_payload,
                    "world_model_highlights": world_model_highlights,
                    "highlight_artifact": str(highlight_artifact) if highlight_artifact else None,
                    "teacher_trace": str(teacher_trace) if teacher_trace else None,
                    "notebook_exports": notebook_exports,
                    "notebook_export_summary": notebook_export_summary,
                },
            )
        )

        return TeacherArtifacts(
            course_plan=course_plan,
            lecture=lecture,
            eval_report=eval_report,
            provenance=provenance,
            manifest=manifest,
            highlights=highlight_artifact,
            teacher_trace=teacher_trace,
            notebook_exports=notebook_exports,
            notebook_export_summary=notebook_export_summary,
        )

    def _log_stage(self, stage_name: str, payload: Dict[str, Any]) -> None:
        self.ctx.provenance.log(
            ProvenanceEvent(
                stage=stage_name,
                message=f"Stage {stage_name} completed",
                agent="apps.orchestrator",
                payload=payload,
            )
        )

    # ------------------------------------------------------------------

    def _run_teacher_loop(
        self,
        ts: str,
        *,
        dataset_summary: Dict[str, Any],
        world_model_highlights: Dict[str, Any] | None,
    ) -> Path | None:
        if not self.ctx.ablations.allow_recursion:
            self.logger.debug("Recursion disabled; teacher loop skipped.")
            return None
        prompt_path = self.ctx.paths.repo_root / "prompts" / "teacher_seed.txt"
        if not prompt_path.exists():
            self.logger.debug("Teacher prompt missing at %s; skipping RLM run", prompt_path)
            return None

        hooks = self._build_teacher_hooks(world_model_highlights)
        for name, func in hooks.items():
            self.teacher_rlm.register_hook(name, func)

        tasks = self._build_teacher_tasks(dataset_summary)
        try:
            run = self.teacher_rlm.run(
                prompt_path=prompt_path,
                context={
                    "course": self.ctx.config.course.model_dump(),
                    "dataset": dataset_summary,
                },
                tasks=tasks,
            )
        except TeacherRLMUnavailable as exc:
            self.logger.warning("Teacher RLM unavailable: %s", exc)
            return None

        for record in run.actions:
            if record.action == "spawn_ta" and isinstance(record.result, dict):
                if record.target == "SyllabusDesigner" and record.result.get("outline"):
                    self._teacher_cache["outline"] = record.result["outline"]
                if record.target == "LectureAuthor" and record.result.get("section"):
                    self._teacher_cache["lecture_section"] = record.result["section"]

        trace_path = self._persist_teacher_trace(ts, run)
        self.ctx.provenance.log(
            ProvenanceEvent(
                stage="teacher_rlm",
                message="Teacher RLM loop executed",
                agent="apps.orchestrator.teacher",
                payload={
                    "mode": run.mode,
                    "prompt_path": str(prompt_path),
                    "actions": len(run.actions),
                    "trace_path": str(trace_path) if trace_path else None,
                },
            )
        )
        return trace_path

    def _build_teacher_tasks(self, dataset_summary: Dict[str, Any]) -> List[TeacherRLMTask]:
        tasks: List[TeacherRLMTask] = []
        tasks.append(
            TeacherRLMTask(
                kind="spawn_ta",
                target="SyllabusDesigner",
                payload={
                    "task": {
                        "focus_areas": getattr(self.ctx.config.course, "focus_areas", []),
                        "dataset": dataset_summary,
                    }
                },
            )
        )
        tasks.append(
            TeacherRLMTask(
                kind="spawn_ta",
                target="LectureAuthor",
                payload={
                    "task": {
                        "module": 1,
                    }
                },
            )
        )
        return tasks

    def _build_teacher_hooks(
        self,
        world_model_highlights: Dict[str, Any] | None,
    ) -> Dict[str, Callable[..., Any]]:
        def use_codeact(program_name: str, **kwargs: Any) -> Dict[str, Any]:
            lm_role = kwargs.pop("lm_role", "teacher")
            result = self._run_codeact_program(program_name, lm_role=lm_role, **kwargs)
            return self._summarize_codeact_result(program_name, result)

        def spawn_ta(role_name: str, **kwargs: Any) -> Dict[str, Any]:
            task = kwargs.get("task") or {}
            return self._execute_ta_role(role_name, task, world_model_highlights)

        def log_event(target: str, **payload: Any) -> Dict[str, Any]:
            entry = {"target": target, **payload}
            return entry

        def wm_snapshot(_: str = "wm_snapshot", **_kwargs: Any) -> Dict[str, Any]:
            return world_model_highlights or {}

        return {
            "use_codeact": use_codeact,
            "spawn_ta": spawn_ta,
            "log_event": log_event,
            "wm_snapshot": wm_snapshot,
        }

    def _summarize_codeact_result(self, program_name: str, result: Any) -> Dict[str, Any]:
        if result is None:
            return {"program": program_name, "status": "empty"}
        payload: Dict[str, Any] = {"program": program_name}
        for attr in ("outline", "section", "corrected_section"):
            if hasattr(result, attr):
                payload[attr] = getattr(result, attr)
        payload.setdefault("repr", repr(result))
        return payload

    def _persist_teacher_trace(self, ts: str, run: TeacherRLMRun) -> Path:
        trace_path = self.ctx.paths.logs_dir / f"teacher-trace-{ts}.json"
        serializable_actions = []
        for record in run.actions:
            serializable_actions.append(
                {
                    "action": record.action,
                    "target": record.target,
                    "payload": record.payload,
                    "result": record.result,
                }
            )
        payload = {
            "mode": run.mode,
            "prompt": str(run.prompt_path),
            "actions": serializable_actions,
            "summary": run.summary,
        }
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return trace_path

    def _execute_ta_role(
        self,
        role_name: str,
        task: Dict[str, Any],
        world_model_highlights: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        if role_name == "SyllabusDesigner":
            outline = self._generate_codeact_plan_outline()
            if outline:
                self._teacher_cache["outline"] = outline
            return {"outline": outline, "task": task}
        if role_name == "LectureAuthor":
            section = self._generate_codeact_lecture_section(world_model_highlights)
            if section:
                self._teacher_cache["lecture_section"] = section
            return {"section": section, "task": task}
        return {"status": "unknown_role", "role": role_name}

    # ------------------------------------------------------------------

    def _emit_course_plan(
        self,
        output_dir: Path,
        dataset_summary: Dict[str, Any],
        world_model_highlights: Dict[str, Any] | None = None,
    ) -> Path:
        course = self.ctx.config.course
        plan_path = output_dir / "course_plan.md"
        codeact_outline = self._generate_codeact_plan_outline()
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
            handle.write("\n")
            if codeact_outline:
                handle.write("## AI-generated Outline (CodeAct)\n")
                handle.write(codeact_outline.strip() + "\n\n")
            highlights = world_model_highlights or {}
            concepts = highlights.get("concepts") or []
            if concepts:
                handle.write("## Concept Highlights\n")
                for concept in concepts:
                    name = concept.get("name") or concept.get("id")
                    summary = (concept.get("summary") or "").strip()
                    summary = summary or "Summary pending in future runs."
                    handle.write(f"- **{name}** ({concept.get('id')}): {summary}\n")
                handle.write("\n")
            timeline = highlights.get("timeline") or []
            if timeline:
                handle.write("## Timeline Signals\n")
                for event in timeline:
                    year = event.get("year") or "n.d."
                    label = event.get("event") or "Milestone"
                    concept_id = event.get("concept_id") or "unknown"
                    handle.write(f"- {year}: {label} · related concept `{concept_id}`\n")
                    summary = (event.get("summary") or "").strip()
                    if summary:
                        handle.write(f"  - {summary}\n")
                handle.write("\n")
            spotlight = highlights.get("spotlight_paper")
            if spotlight:
                handle.write("## Citation Spotlight\n")
                handle.write(
                    f"- {spotlight.get('title')} ({spotlight.get('year')}) — "
                    f"{spotlight.get('venue') or 'venue tbd'}\n\n"
                )
            syllabus = highlights.get("syllabus_modules") or []
            if syllabus:
                handle.write("## Syllabus Snapshot\n")
                for module in syllabus[:3]:
                    week = module.get("week")
                    title = module.get("title") or f"Week {week}"
                    outcomes = module.get("outcomes") or []
                    handle.write(f"- Week {week}: {title}\n")
                    for outcome in outcomes[:2]:
                        handle.write(f"  - {outcome}\n")
                handle.write("\n")
            readings = highlights.get("reading_list") or []
            if readings:
                handle.write("## Suggested Readings\n")
                for rec in readings[:3]:
                    handle.write(
                        f"- {rec.get('title')}: {rec.get('why_it_matters')} ({rec.get('citation')})\n"
                    )
                handle.write("\n")
            exercises = highlights.get("exercise_ideas") or []
            if exercises:
                handle.write("## Practice Ideas\n")
                for exercise in exercises[:3]:
                    handle.write(
                        f"- {exercise.get('title')} ({exercise.get('difficulty')}): "
                        f"{exercise.get('description')}\n"
                    )
                handle.write("\n")
            explainer_chunks = highlights.get("explanations") or []
            if explainer_chunks:
                handle.write("## Explanation Highlights\n")
                for chunk in explainer_chunks[:3]:
                    first_line = (chunk.get("body_md") or "").splitlines()[0:1]
                    summary_line = first_line[0] if first_line else "See explainer section for details."
                    handle.write(f"- **{chunk.get('heading')}** — {summary_line}\n")
                handle.write("\n")
            handle.write("\n> Placeholder plan – replace once Teacher RLM is wired.\n")
        return plan_path

    def _emit_lecture(
        self,
        lecture_dir: Path,
        dataset_summary: Dict[str, Any],
        world_model_highlights: Dict[str, Any] | None = None,
    ) -> Path:
        lecture_path = lecture_dir / "module_01.md"
        codeact_section = self._generate_codeact_lecture_section(world_model_highlights)
        with lecture_path.open("w", encoding="utf-8") as handle:
            handle.write("# Module 1 · Foundations of Database Systems\n\n")
            if codeact_section:
                handle.write(codeact_section.strip() + "\n\n")
            else:
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
            exercises = (world_model_highlights or {}).get("exercise_ideas") or []
            if exercises:
                handle.write("\n## Suggested Practice\n")
                for exercise in exercises[:2]:
                    handle.write(
                        f"- {exercise.get('title')} ({exercise.get('difficulty')}): "
                        f"{exercise.get('description')}\n"
                    )
            readings = (world_model_highlights or {}).get("reading_list") or []
            if readings:
                handle.write("\n## Reading Starter Pack\n")
                for rec in readings[:2]:
                    handle.write(
                        f"- {rec.get('title')} – {rec.get('why_it_matters')}\n"
                    )
            explainer_chunks = (world_model_highlights or {}).get("explanations") or []
            if explainer_chunks:
                handle.write("\n## Background Explainers\n")
                chunk = explainer_chunks[0]
                handle.write(f"### {chunk.get('heading')}\n")
                handle.write(f"{chunk.get('body_md')}\n")
                citations = chunk.get("citations") or []
                if citations:
                    handle.write(f"Citations: {', '.join(citations)}\n")
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
            highlights = world_model_highlights or {}
            concept_highlights = highlights.get("concepts") or []
            if concept_highlights:
                concept = concept_highlights[0]
                handle.write("\n### Spotlight Concept\n")
                handle.write(
                    f"{concept.get('name')} ({concept.get('id')}): "
                    f"{(concept.get('summary') or 'Summary pending.').strip()}\n"
                )
            timeline_highlights = highlights.get("timeline") or []
            if timeline_highlights:
                event = timeline_highlights[0]
                handle.write("\n### Timeline Anchor\n")
                handle.write(
                    f"{event.get('year') or 'n.d.'} – {event.get('event') or 'Milestone'} "
                    f"(related concept `{event.get('concept_id')}`)\n"
                )
                summary = (event.get("summary") or "").strip()
                if summary:
                    handle.write(f"{summary}\n")
            spotlight = highlights.get("spotlight_paper")
            if spotlight:
                handle.write("\n### Citation Preview\n")
                handle.write(
                    f"{spotlight.get('title')} ({spotlight.get('year')}) — "
                    f"{spotlight.get('venue') or 'venue tbd'}\n"
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
        world_model_highlights: Dict[str, Any] | None = None,
        notebook_export_summary: Dict[str, Any] | None = None,
    ) -> Path:
        record = {
            "stage": "teacher_artifacts",
            "message": "Artifacts emitted",
            "agent": "apps.orchestrator",
            "payload": {
                "course_plan": str(course_plan),
                "lecture": str(lecture),
                "world_model_enabled": self.ctx.ablations.use_world_model,
                "students_enabled": self.ctx.ablations.use_students,
                "dataset_summary": dataset_summary,
                "world_model_highlights": world_model_highlights,
                "notebook_export_summary": notebook_export_summary,
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
        world_model_highlights: Dict[str, Any] | None = None,
        highlight_artifact: Path | None = None,
        teacher_trace: Path | None = None,
        notebook_exports: List[Dict[str, Any]] | None = None,
        notebook_export_summary: Dict[str, Any] | None = None,
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
            "world_model_store_exists": snapshot_exists and self.ctx.ablations.use_world_model,
            "evaluation": evaluation_payload,
            "world_model_highlights": world_model_highlights,
            "world_model_highlight_artifact": str(highlight_artifact) if highlight_artifact else None,
            "teacher_trace": str(teacher_trace) if teacher_trace else None,
            "notebook_exports": notebook_exports,
            "notebook_export_summary": notebook_export_summary,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        return path

    def _emit_world_model_highlights_artifact(
        self,
        artifacts_dir: Path,
        ts: str,
        world_model_highlights: Dict[str, Any] | None,
        dataset_summary: Dict[str, Any],
    ) -> Path | None:
        """Persist highlight slices so other scripts can diff/inspect them."""

        if not world_model_highlights:
            return None

        artifact_path = artifacts_dir / f"run-{ts}-highlights.json"
        payload = {
            "timestamp": ts,
            "ablations": self.ctx.ablations.describe(),
            "dataset_summary": dataset_summary,
            "world_model_highlights": world_model_highlights,
        }
        with artifact_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        return artifact_path

    def _generate_codeact_plan_outline(self) -> str | None:
        if not self.ctx.ablations.allow_recursion:
            self.logger.debug("Recursion disabled; skipping CodeAct plan outline.")
            return None
        if not self.ctx.ablations.use_world_model:
            self.logger.debug("World-model ablation enabled; skipping CodeAct plan outline.")
            return None
        cached = self._teacher_cache.get("outline")
        if cached:
            return cached
        if not self.registry:
            return None
        payload = self.ctx.config.course.model_dump()
        result = self._run_codeact_program(
            "PlanCourse",
            constraints=json.dumps(payload, indent=2),
            role="SyllabusDesigner",
            lm_role="ta",
        )
        outline = getattr(result, "outline", None) if result else None
        if outline:
            self.logger.info("CodeAct PlanCourse program succeeded.")
            outline_str = str(outline)
            self._teacher_cache["outline"] = outline_str
            return outline_str
        return None

    def _generate_codeact_lecture_section(
        self, world_model_highlights: Dict[str, Any] | None
    ) -> str | None:
        if not self.ctx.ablations.allow_recursion:
            self.logger.debug("Recursion disabled; skipping CodeAct lecture author.")
            return None
        if not self.ctx.ablations.use_world_model:
            self.logger.debug("World-model ablation enabled; skipping CodeAct lecture author.")
            return None
        cached = self._teacher_cache.get("lecture_section")
        if cached:
            return cached
        if not self.registry:
            return None
        module_payload = self._select_module_payload(world_model_highlights)
        claims_payload = self._build_claim_payload(world_model_highlights)
        lecture_result = self._run_codeact_program(
            "DraftLectureSection",
            module=json.dumps(module_payload, indent=2),
            claims=json.dumps(claims_payload, indent=2),
            role="LectureAuthor",
            lm_role="ta",
        )
        section = getattr(lecture_result, "section", None) if lecture_result else None
        if not section:
            return None
        enforcement = self._run_codeact_program(
            "EnforceCitations",
            md_section=str(section),
            role="LectureAuthor",
            lm_role="ta",
        )
        corrected = getattr(enforcement, "corrected_section", None) if enforcement else None
        final_section = str(corrected or section)
        self.logger.info("DraftLectureSection produced CodeAct content (citations=%s).", bool(corrected))
        self._teacher_cache["lecture_section"] = final_section
        return final_section

    def _run_codeact_program(
        self,
        name: str,
        *,
        role: str | None = None,
        lm_role: str | None = None,
        **kwargs: Any,
    ) -> Any | None:
        if not self.registry:
            return None
        if not self.ctx.ablations.use_world_model and name in WORLD_MODEL_PROGRAMS:
            self.logger.info("World-model ablation enabled; skipping CodeAct program %s", name)
            return None
        allowed = self._allowed_tools_for_role(role)
        lm_handle = self._lm_handle_for_role(lm_role)
        build_kwargs: Dict[str, Any] = {}

        if not self.ctx.ablations.allow_recursion:
            self.logger.info(
                "Recursion disabled; skipping CodeAct program %s", name
            )
            return None

        if allowed is not None:
            build_kwargs["allowed_tools"] = allowed
        if lm_handle is not None and self._build_program_accepts("lm_handle"):
            build_kwargs["lm_handle"] = lm_handle
        try:
            program = self.registry.build_program(name, **build_kwargs)
        except KeyError:
            self.logger.debug("CodeAct program %s not registered.", name)
            return None
        except ValueError as exc:
            self.logger.warning("CodeAct program %s misconfigured: %s", name, exc)
            return None
        try:
            return program(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("CodeAct program %s failed: %s", name, exc)
            return None

    def _lm_handle_for_role(self, lm_role: str | None) -> object | None:
        if not lm_role:
            return None
        handles = getattr(self.ctx, "dspy_handles", None)
        if not handles:
            return None
        normalized = lm_role.lower()
        if normalized == "teacher":
            return handles.teacher
        if normalized in {"ta", "teaching_assistant", "assistant"}:
            return handles.ta
        if normalized == "student":
            return handles.student
        self.logger.debug("Unknown lm_role %s; falling back to default handle", lm_role)
        return None

    def _build_program_accepts(self, parameter: str) -> bool:
        try:
            signature = inspect.signature(self.registry.build_program)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return False
        return parameter in signature.parameters

    def _select_module_payload(self, world_model_highlights: Dict[str, Any] | None) -> Dict[str, Any]:
        modules = (world_model_highlights or {}).get("syllabus_modules") or []
        if modules:
            return modules[0]
        course = self.ctx.config.course
        return {
            "week": 1,
            "title": f"Foundations of {course.title}",
            "outcomes": course.learning_objectives[:3],
            "focus_areas": course.focus_areas[:3] if hasattr(course, "focus_areas") else [],
        }

    def _build_claim_payload(self, world_model_highlights: Dict[str, Any] | None) -> List[Dict[str, Any]]:
        concepts = (world_model_highlights or {}).get("concepts") or []
        claims: List[Dict[str, Any]] = []
        for concept in concepts[:5]:
            claims.append(
                {
                    "concept_id": concept.get("id"),
                    "name": concept.get("name"),
                    "summary": concept.get("summary"),
                }
            )
        if not claims:
            claims.append({"concept_id": "relational_model", "summary": "Relational algebra foundations."})
        return claims

    def _allowed_tools_for_role(self, role: str | None) -> List[str] | None:
        if not role:
            return None
        role_spec = self.ta_roles.get(role)
        if not role_spec:
            self.logger.debug("Unknown TA role %s for CodeAct execution", role)
            return None
        return list(role_spec.tool_whitelist)

    def _notebook_exports_enabled(self) -> bool:
        notebook_cfg = getattr(self.ctx.config, "notebook", None)
        if not notebook_cfg or not getattr(notebook_cfg, "notebook_slug", None):
            return False
        return self.ctx.ablations.allow_recursion

    def _notebook_skip_reason(self) -> str:
        if not self.ctx.ablations.allow_recursion:
            return "recursion_disabled"
        return "notebook_disabled"

    def _collect_world_model_highlights(
        self,
        store_path: Path,
        *,
        concept_limit: int = 3,
        timeline_limit: int = 3,
    ) -> Dict[str, Any]:
        """Return a trimmed slice of the world model for downstream artifacts."""

        highlights = self._collect_dataset_highlights()

        if not self.ctx.ablations.use_world_model or not store_path.exists():
            return highlights

        try:
            concept_rows = fetch_concepts(depth=1, limit=concept_limit, store_path=store_path)
            concept_highlights = [
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "summary": row.get("summary"),
                    "children": row.get("children", []),
                    "prerequisites": row.get("prerequisites", []),
                }
                for row in concept_rows[:concept_limit]
            ]

            timeline_rows = search_events(limit=timeline_limit, store_path=store_path)
            timeline_highlights = timeline_rows[:timeline_limit]

            spotlight_paper: Dict[str, Any] | None = None
            for event in timeline_highlights:
                citation_id = event.get("citation_id")
                if not citation_id:
                    continue
                try:
                    spotlight_paper = lookup_paper(citation_id, store_path=store_path)
                except ValueError:
                    continue
                else:
                    break

            if concept_highlights:
                highlights["concepts"] = concept_highlights
            if timeline_highlights:
                highlights["timeline"] = timeline_highlights
            if spotlight_paper:
                highlights["spotlight_paper"] = spotlight_paper
            return highlights
        except Exception as exc:  # pragma: no cover - defensive guardrail
            self.logger.warning(
                "World-model highlights unavailable: %s",
                exc,
                extra={"store_path": str(store_path)},
            )
            return highlights

    def _collect_dataset_highlights(
        self,
        *,
        module_limit: int = 4,
        reading_limit: int = 5,
        exercise_limit: int = 3,
        timeline_limit: int = 3,
    ) -> Dict[str, Any]:
        dataset_root = self.ctx.config.world_model.dataset_dir
        highlights: Dict[str, Any] = {}
        if not dataset_root.exists():
            return highlights

        try:
            modules = SyllabusDesigner().propose_modules(dataset_root)[:module_limit]
            if modules:
                highlights["syllabus_modules"] = [asdict(module) for module in modules]
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Syllabus designer unavailable: %s", exc)

        try:
            readings = ReadingCurator().curate(dataset_root, limit=reading_limit)
            if readings:
                highlights["reading_list"] = [asdict(rec) for rec in readings]
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Reading curator unavailable: %s", exc)

        try:
            timeline_path = dataset_root / "timeline.csv"
            timeline_events = TimelineSynthesizer().build(timeline_path, limit=timeline_limit)
            serialized = [asdict(event) for event in timeline_events]
            if serialized and "timeline" not in highlights:
                highlights["timeline"] = serialized
        except FileNotFoundError:
            pass
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Timeline synthesizer unavailable: %s", exc)

        try:
            exercises = ExerciseAuthor(dataset_root).draft(limit=exercise_limit)
            if exercises:
                highlights["exercise_ideas"] = [asdict(exercise) for exercise in exercises]
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Exercise author unavailable: %s", exc)

        try:
            explanations = Explainer(dataset_root).write("Database Systems", limit=4)
            if explanations:
                highlights["explanations"] = [asdict(chunk) for chunk in explanations]
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Explainer unavailable: %s", exc)

        return highlights

    def _publish_notebook_sections(
        self,
        course_plan: Path,
        lecture: Path,
    ) -> List[Dict[str, Any]] | None:
        publisher = self._build_notebook_publisher()
        if not publisher:
            return None
        sections: List[NotebookSectionInput] = []
        sections.extend(
            build_sections_from_markdown(
                course_plan,
                fallback_title=self._derive_course_plan_fallback(course_plan),
                max_sections=5,
            )
        )
        sections.extend(
            build_sections_from_markdown(
                lecture,
                fallback_title=self._derive_lecture_fallback(lecture),
                max_sections=3,
            )
        )
        try:
            results = publisher.publish(sections)
            return results or None
        except ValueError as exc:
            self.logger.warning("Notebook export skipped: %s", exc)
            return [
                {
                    "title": "notebook_export",
                    "path": None,
                    "response": {"status": "skipped", "error": str(exc)},
                }
            ]
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("Notebook export failed: %s", exc)
            return [
                {
                    "title": "notebook_export",
                    "path": None,
                    "response": {"status": "error", "error": str(exc)},
                }
            ]

    def _build_notebook_publisher(self) -> NotebookPublisher | None:
        notebook_cfg = getattr(self.ctx.config, "notebook", None)
        if not notebook_cfg:
            return None
        slug = getattr(notebook_cfg, "notebook_slug", None)
        if not slug:
            self.logger.debug("Notebook slug missing; skipping export")
            return None
        course = getattr(self.ctx.config, "course", None)
        description = None
        if course is not None:
            description = getattr(course, "description", None) or getattr(course, "title", None)
        return NotebookPublisher(
            notebook_slug=slug,
            api_base=getattr(notebook_cfg, "api_base", None),
            api_key=getattr(notebook_cfg, "auth_token", None),
            auto_create=getattr(notebook_cfg, "auto_create", True),
            notebook_description=description,
        )

    def _derive_course_plan_fallback(self, course_plan: Path) -> str:
        stem = course_plan.stem.replace("_", " ").strip() or "Course Plan"
        return stem.title()

    def _derive_lecture_fallback(self, lecture: Path) -> str:
        stem = lecture.stem.replace("_", " ").strip() or "lecture"
        return f"Lecture – {stem.title()}"

    def _summarize_notebook_exports(
        self, exports: List[Dict[str, Any]] | None
    ) -> Dict[str, Any] | None:
        if not exports:
            return None
        summary = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "errors": 0,
            "note_ids": [],
            "queued_exports": [],
        }
        success_status = {"ok", "queued", "created", "exists"}
        for entry in exports:
            if isinstance(entry, dict) and entry.get("kind") == "preflight":
                continue
            summary["total"] += 1
            response = entry.get("response") if isinstance(entry, dict) else None
            status = str((response or {}).get("status") or "unknown").lower()
            if status in success_status:
                summary["success"] += 1
            elif status == "skipped":
                summary["skipped"] += 1
            else:
                summary["errors"] += 1

            if isinstance(response, dict):
                note_id = response.get("note_id") or response.get("id")
                if note_id:
                    summary["note_ids"].append(note_id)
                if status == "queued" and response.get("export_path"):
                    summary["queued_exports"].append(response["export_path"])

        return summary

    def _notebook_placeholder(self, reason: str) -> Dict[str, Any]:
        return {
            "title": "notebook_export",
            "path": None,
            "response": {
                "status": "skipped",
                "reason": reason,
            },
        }

    def _apply_mutation(
        self,
        lecture_path: Path,
        iteration: int,
        reason: MutationReason,
        world_model_highlights: Dict[str, Any] | None,
    ) -> Path:
        base_text = lecture_path.read_text(encoding="utf-8")
        refreshed_section = self._generate_codeact_lecture_section(world_model_highlights)
        mutation_note = self._format_mutation_note(iteration, reason)
        if refreshed_section:
            mutated_text = f"{refreshed_section}\n\n---\n### Previous Draft\n{base_text}\n"
        else:
            mutated_text = base_text
        mutated_text = mutated_text.rstrip() + "\n\n" + mutation_note + "\n"
        lecture_path.write_text(mutated_text, encoding="utf-8")
        return lecture_path

    def _format_mutation_note(self, iteration: int, reason: MutationReason) -> str:
        lines = [
            f"Pass {iteration}: overall={reason.overall_score:.3f}, quiz_pass_rate={reason.quiz_pass_rate:.3f}.",
        ]
        if reason.failing_rubrics:
            lines.append("Failing rubrics: " + ", ".join(reason.failing_rubrics))
        if reason.failing_questions:
            lines.append("Quiz gaps: " + ", ".join(reason.failing_questions))
        bullet_list = "\n".join(f"- {line}" for line in lines)
        return f"## Mutation Pass {iteration}\n{bullet_list}"

    def _evaluate_artifacts(
        self,
        lecture_path: Path,
        world_model_highlights: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        if not self.ctx.ablations.use_students:
            return {"use_students": False, "status": "students_disabled"}

        evaluation_cfg = self.ctx.config.evaluation
        rubrics_path = evaluation_cfg.rubrics_path
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

        try:
            quiz_engine = StudentQuizEvaluator(
                evaluation_cfg.quiz_bank_path,
                pass_threshold=evaluation_cfg.quiz_pass_threshold,
                question_limit=evaluation_cfg.quiz_question_limit,
            )
        except FileNotFoundError:
            return {
                "use_students": False,
                "status": "missing_quiz_bank",
                "quiz_bank_path": str(evaluation_cfg.quiz_bank_path),
            }
        except ValueError as exc:
            return {
                "use_students": False,
                "status": "invalid_quiz_bank",
                "error": str(exc),
                "quiz_bank_path": str(evaluation_cfg.quiz_bank_path),
            }

        loop_runner = StudentLoopRunner(
            grader=grader,
            quiz_evaluator=quiz_engine,
            config=StudentLoopConfig(
                rubric_threshold=evaluation_cfg.rubric_pass_threshold,
                quiz_threshold=evaluation_cfg.quiz_pass_threshold,
                max_mutations=evaluation_cfg.max_mutations,
            ),
            mutation_callback=lambda path, iteration, reason: self._apply_mutation(
                path,
                iteration,
                reason,
                world_model_highlights,
            ),
        )
        results = loop_runner.run(lecture_path)
        results.update(
            {
                "rubrics_path": str(rubrics_path),
                "quiz_bank_path": str(evaluation_cfg.quiz_bank_path),
            }
        )
        return results
