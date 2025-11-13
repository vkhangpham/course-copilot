import { Activity, BadgePercent, BookOpenCheck, Download, NotebookPen, Sparkles } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { NotebookExportEntry, RunDetail, ScientificMetrics } from "@/lib/api";

const PORTAL_API_BASE = process.env.NEXT_PUBLIC_PORTAL_API_BASE ?? "http://localhost:8001";

function formatHighlightSource(value?: string | null): string | undefined {
  if (!value) {
    return undefined;
  }
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

export function RunDetailSection({ detail }: { detail: RunDetail | null }) {
  const highlights = (detail?.manifest?.["world_model_highlights"] as Record<string, unknown>) || {};
  const concepts = (highlights["concepts"] as { id: string; summary?: string }[]) || [];
  const timeline = (highlights["timeline"] as { year?: string; event?: string; summary?: string }[]) || [];
  const highlightSourceRaw =
    (typeof detail?.highlight_source === "string" && detail.highlight_source) ||
    (typeof detail?.manifest?.["highlight_source"] === "string"
      ? (detail?.manifest?.["highlight_source"] as string)
      : undefined);
  const highlightSource = highlightSourceRaw?.toLowerCase();
  const formattedHighlightSource = formatHighlightSource(highlightSourceRaw);
  const highlightTitle =
    highlightSource === "dataset"
      ? "Dataset highlights"
      : highlightSource && highlightSource !== "world_model"
        ? `${formattedHighlightSource ?? "Highlights"} highlights`
        : "World-model highlights";
  const highlightDescription =
    highlightSource === "dataset"
      ? "Summary pulled directly from the handcrafted dataset when the world model ablation is enabled."
      : "Key modules, timeline beats, and exercises derived from the current world model snapshot.";
  const highlightBadgeText =
    highlightSource === "dataset"
      ? "Dataset fallback"
      : highlightSource && highlightSource !== "world_model"
        ? formattedHighlightSource ?? "Custom"
        : "World model";
  const highlightBadgeVariant = highlightSource === "dataset" ? "secondary" : "outline";
  const rubrics = detail?.evaluation?.rubrics ?? [];
  const evaluationAttempts = detail?.evaluation_attempts ?? [];
  const notebookSlug = detail?.notebook_slug ?? process.env.NEXT_PUBLIC_PORTAL_NOTEBOOK_SLUG;
  const notebookBase = process.env.NEXT_PUBLIC_NOTEBOOK_BASE;
  const notebookUrl =
    notebookSlug && notebookBase ? `${notebookBase.replace(/\/$/, "")}/notebook/${notebookSlug}` : undefined;
  const triggerRunUrl = process.env.NEXT_PUBLIC_TRIGGER_RUN_URL ?? "#";
  const ablationFlags = [
    { key: "use_world_model", label: "World model", enabled: detail?.ablations?.use_world_model ?? true },
    { key: "use_students", label: "Student graders", enabled: detail?.ablations?.use_students ?? true },
    { key: "allow_recursion", label: "Recursion", enabled: detail?.ablations?.allow_recursion ?? true },
  ];
  const traceFiles = detail?.trace_files ?? [];
  const manifest = detail?.manifest as Record<string, unknown> | undefined;
  const manifestExportsRaw = Array.isArray(manifest?.["notebook_exports"])
    ? (manifest?.["notebook_exports"] as unknown[])
    : [];
  const manifestExports = manifestExportsRaw.filter((entry) => {
    const kind = typeof entry === "object" && entry !== null ? (entry as { kind?: string }).kind : undefined;
    return (kind ?? "").toLowerCase() !== "preflight";
  }) as NotebookExportEntry[];
  const notebookExports = (detail?.notebook_exports && detail.notebook_exports.length > 0
    ? detail.notebook_exports
    : manifestExports) as NotebookExportEntry[];
  const actualNotebookExportCount = notebookExports.filter(
    (entry) => (entry.status ?? "").toLowerCase() !== "skipped",
  ).length;
  const coursePlanUrl = detail ? `${PORTAL_API_BASE}/runs/${detail.run_id}/course-plan` : null;
  const lectureUrl = detail ? `${PORTAL_API_BASE}/runs/${detail.run_id}/lecture` : null;
  const scienceArtifactPath =
    (typeof detail?.scientific_metrics_artifact === "string" && detail.scientific_metrics_artifact) ||
    (typeof manifest?.["scientific_metrics_artifact"] === "string"
      ? (manifest?.["scientific_metrics_artifact"] as string)
      : undefined);
  const scienceDownloadUrl = scienceArtifactPath
    ? `${PORTAL_API_BASE}/${scienceArtifactPath.replace(/^\//, "")}`
    : null;
  const scienceConfigPath =
    (typeof detail?.science_config_path === "string" && detail.science_config_path) ||
    (typeof manifest?.["science_config_path"] === "string"
      ? (manifest?.["science_config_path"] as string)
      : undefined);
  const portalScientificMetrics =
    (detail?.scientific_metrics as ScientificMetrics | undefined) ??
    (manifest?.["scientific_metrics"] as ScientificMetrics | undefined);
  type ScientificMetricRow = { label: string; detail: string; value: number };
  const scientificRows: ScientificMetricRow[] = (
    [
      {
        label: "Bloom's alignment",
        detail: "Curriculum coverage across Bloom's taxonomy",
        value: portalScientificMetrics?.pedagogical?.blooms_alignment as number | undefined,
      },
      {
        label: "Learning-path coherence",
        detail: "How well modules build on each other",
        value: portalScientificMetrics?.pedagogical?.learning_path_coherence as number | undefined,
      },
      {
        label: "Citation validity",
        detail: "Grounding of claims against sources",
        value: portalScientificMetrics?.content_quality?.citation_validity as number | undefined,
      },
      {
        label: "Citation coverage",
        detail: "Share of sections with supporting citations",
        value: portalScientificMetrics?.content_quality?.citation_coverage as number | undefined,
      },
      {
        label: "Predicted retention",
        detail: "Estimated learner retention after this lecture",
        value: portalScientificMetrics?.learning_outcomes?.predicted_retention as number | undefined,
      },
    ] as { label: string; detail: string; value: number | undefined }[]
  ).filter((entry): entry is ScientificMetricRow => typeof entry.value === "number" && !Number.isNaN(entry.value));
  const hasScientificMetrics = scientificRows.length > 0;

  return (
    <section className="mx-auto w-full max-w-6xl px-6 py-14">
      <div className="mb-12 flex flex-col gap-6 rounded-3xl border border-slate-100 bg-white/80 p-8 shadow-xl shadow-slate-200/40">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-sky-600">CourseGen Portal</p>
            <h1 className="mt-2 text-4xl font-bold text-slate-900">Database Systems pipeline overview</h1>
            <p className="mt-3 text-lg text-slate-600">
              Inspect orchestrator runs, student rubric scores, world-model highlights, and notebook exports. The
              dashboard reflects the latest artifacts emitted by `coursegen-poc`.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild disabled={!notebookUrl}>
              <Link href={notebookUrl ?? "#"} className="flex items-center gap-2" aria-disabled={!notebookUrl}>
                <NotebookPen className="h-4 w-4" /> {notebookSlug ? "Open Notebook" : "Notebook pending"}
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href={triggerRunUrl} className="flex items-center gap-2">
                <Sparkles className="h-4 w-4" /> Trigger new run
              </Link>
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Latest run</CardTitle>
              <Activity className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{detail ? detail.run_id : "—"}</div>
              <p className="text-xs text-muted-foreground">
                {detail ? new Date(detail.created_at).toLocaleString() : "Awaiting orchestrator run"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Overall score</CardTitle>
              <BookOpenCheck className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {detail?.evaluation?.overall_score !== undefined
                  ? detail.evaluation.overall_score?.toFixed?.(2) ?? detail.evaluation.overall_score
                  : "—"}
              </div>
              <p className="text-xs text-muted-foreground">Cumulative rubric score</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Notebook exports</CardTitle>
              <BadgePercent className="h-4 w-4 text-slate-400" />
            </CardHeader>
              <CardContent>
              <div className="text-2xl font-bold">{actualNotebookExportCount || "—"}</div>
              <p className="text-xs text-muted-foreground">Sections pushed this run</p>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle>{highlightTitle}</CardTitle>
              <CardDescription>{highlightDescription}</CardDescription>
            </div>
            <Badge variant={highlightBadgeVariant} className="w-fit">
              {highlightBadgeText}
            </Badge>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-2">
            {concepts.slice(0, 3).map((concept) => (
              <div key={concept.id} className="rounded-lg border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-sm font-semibold text-slate-900">{concept.id}</p>
                <p className="text-sm text-muted-foreground">{concept.summary || "Summary coming soon."}</p>
              </div>
            ))}
            {timeline.slice(0, 3).map((event, idx) => (
              <div key={`timeline-${idx}`} className="rounded-lg border border-slate-100 bg-slate-50/80 p-4">
                <div className="flex items-center justify-between text-sm font-semibold">
                  <span>{event.event || "Milestone"}</span>
                  <span className="text-xs text-muted-foreground">{event.year || "n.d."}</span>
                </div>
                <p className="text-sm text-muted-foreground">{event.summary || "Context coming soon."}</p>
              </div>
            ))}
            {concepts.length === 0 && timeline.length === 0 && (
              <p className="text-sm text-muted-foreground">Highlights will appear after the first orchestrator run.</p>
            )}
          </CardContent>
        </Card>
        <div className="space-y-6 md:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Student rubric outcomes</CardTitle>
              <CardDescription>Scores reported by the simulated student graders.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {rubrics.length === 0 && <p className="text-sm text-muted-foreground">No rubric scores recorded yet.</p>}
              {rubrics.map((rubric) => (
                <div key={rubric.name} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold">{rubric.name}</p>
                    {rubric.score !== undefined && (
                      <p className="text-xs text-muted-foreground">Score: {rubric.score?.toFixed?.(2) ?? rubric.score}</p>
                    )}
                  </div>
                  <Badge variant={rubric.passed ? "success" : "destructive"}>{rubric.passed ? "PASS" : "FAIL"}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Scientific metrics</CardTitle>
              <CardDescription>Signals from the scientific evaluator loop.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!hasScientificMetrics && (
                <p className="text-sm text-muted-foreground">
                  Scientific metrics will appear after the evaluator runs on a completed lecture.
                </p>
              )}
              {hasScientificMetrics && (
                <div className="space-y-3">
                  {scientificRows.map((row) => (
                    <div key={row.label} className="rounded-lg border border-slate-100 px-3 py-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold">{row.label}</p>
                        <Badge variant="outline">{formatScore(row.value)}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">{row.detail}</p>
                    </div>
                  ))}
                </div>
              )}
              {scienceDownloadUrl && (
                <Button variant="secondary" className="w-full" asChild>
                  <Link href={scienceDownloadUrl} target="_blank" className="flex items-center justify-center gap-2">
                    <Download className="h-4 w-4" /> Download metrics JSON
                  </Link>
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Ablation state</CardTitle>
            <CardDescription>Which subsystems ran for the latest pipeline execution.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {ablationFlags.map((flag) => (
              <div key={flag.key} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                <div>
                  <p className="text-sm font-semibold">{flag.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {flag.enabled ? "Enabled for this run" : "Disabled via CLI ablation"}
                  </p>
                </div>
                <Badge variant={flag.enabled ? "secondary" : "destructive"}>
                  {flag.enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Teacher trace</CardTitle>
            <CardDescription>Summary of the teacher RLM run.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!detail?.teacher_trace && <p className="text-sm text-muted-foreground">Teacher trace not available yet.</p>}
            {detail?.teacher_trace && (
              <div className="space-y-2">
                <p className="text-sm font-semibold">{detail.teacher_trace.summary ?? "No summary provided"}</p>
                <p className="text-xs text-muted-foreground">Actions: {detail.teacher_trace.action_count}</p>
                {detail.teacher_trace.prompt && (
                  <p className="text-xs text-muted-foreground">Prompt: {detail.teacher_trace.prompt}</p>
                )}
                <Button variant="secondary" asChild>
                  <Link href={`${PORTAL_API_BASE}/runs/${detail.run_id}/traces/teacher_trace`} target="_blank">
                    Download trace
                  </Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Artifacts & downloads</CardTitle>
            <CardDescription>Raw course plan, lecture, and trace files.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {!detail && <p className="text-sm text-muted-foreground">Artifacts appear after the first run.</p>}
            {detail && (
              <div className="space-y-2">
                <ArtifactLink label="Course plan" href={coursePlanUrl} />
                <ArtifactLink label="Lecture" href={lectureUrl} />
                <ArtifactLink label="Scientific metrics (JSON)" href={scienceDownloadUrl} />
                {scienceConfigPath && (
                  <p className="break-all text-xs text-muted-foreground">
                    science config: <span className="font-mono">{scienceConfigPath}</span>
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Notebook exports</CardTitle>
            <CardDescription>Most recent sections pushed to the target Notebook.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {notebookExports.length === 0 && (
              <p className="text-sm text-muted-foreground">No exports recorded yet.</p>
            )}
            {notebookExports.map((entry, idx) => {
              const status = entry.status ?? "unknown";
              const badgeVariant =
                status === "ok" || status === "created"
                  ? "success"
                  : status === "queued"
                    ? "secondary"
                    : status === "skipped"
                      ? "outline"
                      : "destructive";
              const noteId = entry.note_id ?? entry.section_id;
              return (
                <div key={`${entry.title}-${idx}`} className="rounded-lg border border-slate-100 p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold">{entry.title ?? `Section ${idx + 1}`}</p>
                      <p className="text-xs text-muted-foreground">Citations: {entry.citations?.length ?? 0}</p>
                    </div>
                    <Badge variant={badgeVariant}>{status}</Badge>
                  </div>
                  {noteId && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Note ID: <span className="font-mono">{noteId}</span>
                    </p>
                  )}
              {entry.path && (
                <p className="text-xs text-muted-foreground break-all">
                  Source: <span className="font-mono">{entry.path}</span>
                </p>
              )}
              {entry.notebook && (
                <p className="text-xs text-muted-foreground">Notebook: {entry.notebook}</p>
              )}
              {entry.reason && (
                <p className="text-xs text-muted-foreground">Reason: {entry.reason}</p>
              )}
              {entry.error && (
                <p className="text-xs text-destructive">Error: {entry.error}</p>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>

        <Card>
          <CardHeader>
            <CardTitle>Trace files</CardTitle>
            <CardDescription>Downloadable provenance, evaluation, and log artifacts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {traceFiles.length === 0 && <p className="text-sm text-muted-foreground">No trace files published yet.</p>}
            {traceFiles.map((trace) => (
              <div key={trace.name} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2">
                <div>
                  <p className="text-sm font-semibold">{trace.label}</p>
                  <p className="text-xs text-muted-foreground">{trace.name}</p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href={`${PORTAL_API_BASE}/runs/${detail?.run_id}/traces/${trace.name}`} target="_blank">
                    <Download className="mr-2 h-4 w-4" /> Download
                  </Link>
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mutation attempts</CardTitle>
            <CardDescription>Quiz pass rates and triggers recorded by the student loop.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {evaluationAttempts.length === 0 && (
              <p className="text-sm text-muted-foreground">No mutation attempts recorded.</p>
            )}
            {evaluationAttempts.map((attempt) => {
              const failingRubrics = attempt.failing_rubrics ?? [];
              const failingQuestions = attempt.failing_questions ?? [];
              const quizPercent =
                typeof attempt.quiz_pass_rate === "number" ? Math.round(attempt.quiz_pass_rate * 100) : null;
              return (
                <div key={attempt.iteration} className="rounded-lg border border-slate-100 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold">Iteration {attempt.iteration}</p>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant={(attempt.overall_score ?? 0) >= 0.7 ? "success" : "secondary"}>
                        Score {formatScore(attempt.overall_score)}
                      </Badge>
                      {quizPercent !== null && (
                        <Badge variant={quizPercent >= 75 ? "success" : "destructive"}>Quiz {quizPercent}%</Badge>
                      )}
                    </div>
                  </div>
                  {failingRubrics.length > 0 && (
                    <p className="mt-2 text-xs text-muted-foreground">Failing rubrics: {failingRubrics.join(", ")}</p>
                  )}
                  {failingQuestions.length > 0 && (
                    <p className="text-xs text-muted-foreground">Quiz gaps: {failingQuestions.join(", ")}</p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function ArtifactLink({ label, href }: { label: string; href: string | null }) {
  if (!href) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-dashed border-slate-200 px-3 py-2 text-sm text-muted-foreground">
        <span>{label}</span>
        <span>Unavailable</span>
      </div>
    );
  }
  return (
    <Link
      href={href}
      target="_blank"
      className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
    >
      <span>{label}</span>
      <Download className="h-4 w-4" />
    </Link>
  );
}

function formatScore(value?: number | null): string {
  if (typeof value === "number") {
    return value.toFixed(2);
  }
  return "n/a";
}
