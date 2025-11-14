"""Stubbed Teacher/TA orchestration that integrates with ccopilot.pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from apps.codeact.registry import CodeActRegistry
from apps.codeact.tools.world_model import fetch_concepts, lookup_paper, search_events
from apps.orchestrator.ta_roles.exercise_author import ExerciseAuthor
from apps.orchestrator.ta_roles.explainer import Explainer
from apps.orchestrator.ta_roles.reading_curator import ReadingCurator
from apps.orchestrator.ta_roles.syllabus_designer import SyllabusDesigner
from apps.orchestrator.ta_roles.timeline_synthesizer import TimelineSynthesizer
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
    highlights: Path | None = None
    highlight_source: str | None = None
    notebook_exports: List[Dict[str, Any]] | None = None
    notebook_export_summary: Dict[str, Any] | None = None


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

        world_model_highlights, highlight_source = self._collect_world_model_highlights(world_model_store)
        if not self.ctx.ablations.use_world_model:
            highlight_source = highlight_source or "dataset"
        highlight_artifact = self._emit_world_model_highlights_artifact(
            manifest_dir,
            ts,
            world_model_highlights,
            dataset_summary,
        )

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
                    "codeact_programs": (self.registry.describe()["programs"] if self.registry else {}),
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
        notebook_exports = [self._notebook_placeholder(reason="notebook_stubbed")]
        notebook_summary = self._summarize_notebook_exports(notebook_exports)
        provenance = self._emit_provenance_record(
            prov_dir / f"run-{ts}.jsonl",
            course_plan,
            lecture,
            dataset_summary,
            highlight_source,
            world_model_highlights,
            notebook_exports,
            notebook_summary,
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
            highlight_artifact,
            highlight_source=highlight_source,
            notebook_exports=notebook_exports,
            notebook_export_summary=notebook_summary,
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
                    "highlight_source": highlight_source,
                    "highlight_artifact": str(highlight_artifact) if highlight_artifact else None,
                },
            )
        )

        return PipelineArtifacts(
            course_plan=course_plan,
            lecture=lecture,
            eval_report=eval_report,
            provenance=provenance,
            manifest=manifest,
            highlights=highlight_artifact,
            highlight_source=highlight_source,
            notebook_exports=notebook_exports,
            notebook_export_summary=notebook_summary,
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
                handle.write(f"- Domains: {', '.join(dataset_summary['top_domains'])}\n")
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
                handle.write(f"- {spotlight.get('title')} ({spotlight.get('year')}) — {spotlight.get('venue') or 'venue tbd'}\n\n")
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
                    handle.write(f"- {rec.get('title')}: {rec.get('why_it_matters')} ({rec.get('citation')})\n")
                handle.write("\n")
            exercises = highlights.get("exercise_ideas") or []
            if exercises:
                handle.write("## Practice Ideas\n")
                for exercise in exercises[:3]:
                    handle.write(f"- {exercise.get('title')} ({exercise.get('difficulty')}): {exercise.get('description')}\n")
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

    def _emit_placeholder_lecture(
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
                handle.write("This stub is generated while the TA CodeAct loop is under construction.\n")
                handle.write("Each real run will include citations, examples, and student prompts.\n")
            focus = (dataset_summary.get("top_domains") or ["Database Systems"])[0]
            handle.write(f"\n_Current dataset focus: {focus}_\n")
            handle.write("\n## Learning Objectives & Assessments\n")
            handle.write("- Learning objective: Explain the relational model, SQL, and why normalization matters.\n")
            handle.write("- Assessment strategy: short concept quizzes plus a transactional lab on locking and recovery.\n\n")
            handle.write("## Concept Coverage\n")
            handle.write("We revisit relational algebra and SQL before contrasting concurrency control mechanisms,")
            handle.write(" recovery logs, and distributed systems such as Spanner and resilient NewSQL engines.\n\n")
            handle.write("## Worked Example\n")
            handle.write("Consider a banking workload: a transaction debits one account and credits another. ")
            handle.write("We trace how two-phase locking prevents lost updates while recovery replays committed entries.\n\n")
            handle.write("## Review Questions\n")
            handle.write(
                "1. Why does strict two-phase locking guarantee serializability?\n"
                "2. Which SQL query would expose a partial failure in the example above?\n"
            )
            exercises = (world_model_highlights or {}).get("exercise_ideas") or []
            if exercises:
                handle.write("\n## Suggested Practice\n")
                for exercise in exercises[:2]:
                    handle.write(f"- {exercise.get('title')} ({exercise.get('difficulty')}): {exercise.get('description')}\n")
            readings = (world_model_highlights or {}).get("reading_list") or []
            if readings:
                handle.write("\n## Reading Starter Pack\n")
                for rec in readings[:2]:
                    handle.write(f"- {rec.get('title')} – {rec.get('why_it_matters')}\n")
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
            handle.write("- Codd (1970) formalized the relational model and relational algebra [`codd-1970`].\n")
            handle.write("- System R (1976) demonstrated cost-based SQL optimization and transactions [`system-r-1976`].\n")
            handle.write("- Postgres, ARIES, and Spanner extend these ideas to modern distributed databases.\n")
            highlights = world_model_highlights or {}
            concept_highlights = highlights.get("concepts") or []
            if concept_highlights:
                concept = concept_highlights[0]
                handle.write("\n### Spotlight Concept\n")
                handle.write(f"{concept.get('name')} ({concept.get('id')}): {(concept.get('summary') or 'Summary pending.').strip()}\n")
            timeline_highlights = highlights.get("timeline") or []
            if timeline_highlights:
                event = timeline_highlights[0]
                handle.write("\n### Timeline Anchor\n")
                handle.write(
                    f"{event.get('year') or 'n.d.'} – {event.get('event') or 'Milestone'} (related concept `{event.get('concept_id')}`)\n"
                )
                summary = (event.get("summary") or "").strip()
                if summary:
                    handle.write(f"{summary}\n")
            spotlight = highlights.get("spotlight_paper")
            if spotlight:
                handle.write("\n### Citation Preview\n")
                handle.write(f"{spotlight.get('title')} ({spotlight.get('year')}) — {spotlight.get('venue') or 'venue tbd'}\n")
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
        highlight_source: str | None,
        world_model_highlights: Dict[str, Any] | None = None,
        notebook_exports: List[Dict[str, Any]] | None = None,
        notebook_export_summary: Dict[str, Any] | None = None,
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
                "world_model_highlights": world_model_highlights or {},
                "highlight_source": highlight_source,
                "notebook_exports": notebook_exports,
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
        *,
        highlight_source: str | None = None,
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
            "world_model_store_exists": snapshot_exists,
            "evaluation": evaluation_payload,
            "world_model_highlights": world_model_highlights or {},
            "world_model_highlight_artifact": str(highlight_artifact) if highlight_artifact else None,
            "highlight_source": highlight_source,
            "notebook_exports": notebook_exports,
            "notebook_export_summary": notebook_export_summary,
            "science_config_path": (str(self.ctx.science_config_path) if self.ctx.science_config_path else None),
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
        if not self.registry:
            return None
        payload = self.ctx.config.course.model_dump()
        result = self._run_codeact_program(
            "PlanCourse",
            constraints=json.dumps(payload, indent=2),
        )
        outline = getattr(result, "outline", None) if result else None
        if outline:
            self.logger.info("CodeAct PlanCourse program succeeded.")
            return str(outline)
        return None

    def _generate_codeact_lecture_section(self, world_model_highlights: Dict[str, Any] | None) -> str | None:
        if not self.registry:
            return None
        module_payload = self._select_module_payload(world_model_highlights)
        claims_payload = self._build_claim_payload(world_model_highlights)
        lecture_result = self._run_codeact_program(
            "DraftLectureSection",
            module=json.dumps(module_payload, indent=2),
            claims=json.dumps(claims_payload, indent=2),
        )
        section = getattr(lecture_result, "section", None) if lecture_result else None
        if not section:
            return None
        enforcement = self._run_codeact_program(
            "EnforceCitations",
            md_section=str(section),
        )
        corrected = getattr(enforcement, "corrected_section", None) if enforcement else None
        final_section = str(corrected or section)
        self.logger.info("DraftLectureSection produced CodeAct content (citations=%s).", bool(corrected))
        return final_section

    def _run_codeact_program(self, name: str, **kwargs: Any) -> Any | None:
        if not self.registry:
            return None
        try:
            program = self.registry.build_program(name)
        except KeyError:
            self.logger.debug("CodeAct program %s not registered.", name)
            return None
        try:
            return program(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("CodeAct program %s failed: %s", name, exc)
            return None

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

    def _collect_world_model_highlights(
        self,
        store_path: Path,
        *,
        concept_limit: int = 3,
        timeline_limit: int = 3,
    ) -> tuple[Dict[str, Any], str | None]:
        """Return a trimmed slice of the world model for placeholder artifacts."""

        highlights = self._collect_dataset_highlights()
        # Even when the dataset highlight slice is empty we still want the manifest
        # to record that the world-model data was unavailable and we fell back to
        # handcrafted assets. This keeps ablation provenance visible in the portal
        # and CLI summaries.
        fallback_label = "dataset"

        if not self.ctx.ablations.use_world_model or not store_path.exists():
            return highlights, fallback_label

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

            sourced_from_world_model = False
            if concept_highlights:
                highlights["concepts"] = concept_highlights
                sourced_from_world_model = True
            if timeline_highlights:
                highlights["timeline"] = timeline_highlights
                sourced_from_world_model = True
            if spotlight_paper:
                highlights["spotlight_paper"] = spotlight_paper
                sourced_from_world_model = True
            return highlights, ("world_model" if sourced_from_world_model else fallback_label)
        except Exception as exc:  # pragma: no cover - defensive guardrail
            self.logger.warning(
                "World-model highlights unavailable: %s",
                exc,
                extra={"store_path": str(store_path)},
            )
            return highlights, fallback_label

    @staticmethod
    def _notebook_placeholder(*, reason: str) -> Dict[str, Any]:
        return {
            "title": "notebook_export",
            "path": None,
            "citations": [],
            "response": {
                "status": "skipped",
                "reason": reason,
            },
        }

    @staticmethod
    def _summarize_notebook_exports(exports: List[Dict[str, Any]] | None) -> Dict[str, Any] | None:
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
            response = entry.get("response") if isinstance(entry, dict) else None
            if isinstance(entry, dict) and entry.get("kind") == "preflight":
                continue
            summary["total"] += 1
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
