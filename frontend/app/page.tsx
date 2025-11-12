import { Activity, BookOpenCheck, NotebookPen, Sparkles } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchRunDetail, fetchRuns } from "@/lib/api";

async function loadData() {
  try {
    const runs = await fetchRuns();
    const latest = runs[0];
    const detail = latest ? await fetchRunDetail(latest.run_id) : null;
    return { runs, detail };
  } catch (error) {
    console.warn("Portal backend unavailable", error);
    return { runs: [], detail: null };
  }
}

export default async function Page() {
  const { runs, detail } = await loadData();
  const highlights = (detail?.manifest?.world_model_highlights as Record<string, unknown>) || {};
  const concepts = (highlights["concepts"] as { id: string; summary?: string }[]) || [];
  const timeline = (highlights["timeline"] as { year?: string; event?: string; summary?: string }[]) || [];
  const rubrics = detail?.evaluation?.rubrics ?? [];
  const notebookSlug = detail?.notebook_slug ?? process.env.NEXT_PUBLIC_PORTAL_NOTEBOOK_SLUG;
  const notebookBase = process.env.NEXT_PUBLIC_NOTEBOOK_BASE;
  const notebookUrl =
    notebookSlug && notebookBase
      ? `${notebookBase.replace(/\\/$/, "")}/notebook/${notebookSlug}`
      : undefined;
  const triggerRunUrl = process.env.NEXT_PUBLIC_TRIGGER_RUN_URL ?? "#";

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="absolute inset-x-0 top-0 -z-10 flex justify-center">
        <div className="h-[320px] w-[480px] rounded-full bg-sky-200/40 blur-[120px]" />
      </div>
      <div className="mx-auto w-full max-w-6xl px-6 py-14">
        <section className="mb-12 flex flex-col gap-6 rounded-3xl border border-slate-100 bg-white/80 p-8 shadow-xl shadow-slate-200/40">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-sky-600">CourseGen Portal</p>
              <h1 className="mt-2 text-4xl font-bold text-slate-900">Database Systems pipeline overview</h1>
              <p className="mt-3 text-lg text-slate-600">
                Inspect the latest orchestrator run, student rubric scores, and world-model highlights. The
                UI updates automatically whenever `coursegen-poc` emits new artifacts.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button asChild disabled={!notebookUrl}>
                <Link
                  href={notebookUrl ?? "#"}
                  className="flex items-center gap-2"
                  aria-disabled={!notebookUrl}
                  tabIndex={notebookUrl ? 0 : -1}
                >
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
                    ? detail.evaluation.overall_score?.toFixed(2)
                    : "n/a"}
                </div>
                <p className="text-xs text-muted-foreground">Student rubric average</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Runs tracked</CardTitle>
                <Activity className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{runs.length}</div>
                <p className="text-xs text-muted-foreground">Artifacts discovered in outputs/artifacts</p>
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>World-model highlights</CardTitle>
              <CardDescription>Concepts and timeline slices extracted from the latest manifest.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {concepts.length === 0 && <p className="text-sm text-muted-foreground">No concept highlights available yet.</p>}
              {concepts.slice(0, 3).map((concept) => (
                <div key={concept.id} className="rounded-lg border border-dashed border-slate-200 p-3">
                  <div className="text-sm font-semibold">{concept.id}</div>
                  <p className="text-sm text-muted-foreground">{concept.summary || "Summary pending."}</p>
                </div>
              ))}
              {timeline.slice(0, 3).map((event, idx) => (
                <div key={`timeline-${idx}`} className="rounded-lg border border-slate-100 bg-slate-50/80 p-3">
                  <div className="flex items-center justify-between text-sm font-medium">
                    <span>{event.event || "Milestone"}</span>
                    <span className="text-xs text-muted-foreground">{event.year || "n.d."}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{event.summary || "Context coming soon."}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Student rubric outcomes</CardTitle>
              <CardDescription>Each rubric reflects the simulated student agents.</CardDescription>
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
        </section>
      </div>
    </main>
  );
}
