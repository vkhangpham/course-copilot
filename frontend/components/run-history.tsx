import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { RunListItem } from "@/lib/api";

export function RunHistory({ runs, activeRunId }: { runs: RunListItem[]; activeRunId?: string }) {
  return (
    <section className="mx-auto w-full max-w-6xl px-6 pb-16">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Run history</h2>
          <p className="text-sm text-muted-foreground">Latest orchestrator executions</p>
        </div>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Runs</CardTitle>
          <CardDescription>Click a run to inspect its details.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {runs.length === 0 && <p className="px-4 py-6 text-sm text-muted-foreground">No runs captured yet.</p>}
          <div className="divide-y">
            {runs.map((run) => (
              <Link
                key={run.run_id}
                href={`/runs/${run.run_id}`}
                className="flex items-center justify-between px-4 py-3 transition hover:bg-slate-50"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-900">{run.run_id}</p>
                  <p className="text-xs text-muted-foreground">{new Date(run.created_at).toLocaleString()}</p>
                  <ScientificMetricBadges metrics={run.scientific_metrics} />
                  <AblationBadges ablations={run.ablations} />
                  <ScienceConfigHint path={run.science_config_path} />
                </div>
                <div className="flex items-center gap-3">
                  {typeof run.highlight_source === "string" && run.highlight_source.length > 0 && (
                    <Badge variant="secondary">
                      {run.highlight_source === "world_model"
                        ? "World model"
                        : run.highlight_source === "dataset"
                          ? "Dataset"
                          : run.highlight_source}
                    </Badge>
                  )}
                  {typeof run.overall_score === "number" && (
                    <Badge variant="outline">{run.overall_score.toFixed(2)}</Badge>
                  )}
                  {run.notebook_export_summary && (
                    <Badge
                      variant={
                        (run.notebook_export_summary.success ?? 0) === (run.notebook_export_summary.total ?? 0)
                          ? "success"
                          : (run.notebook_export_summary.errors ?? 0) > 0
                            ? "destructive"
                            : "secondary"
                      }
                    >
                      NB {run.notebook_export_summary.success ?? 0}/{run.notebook_export_summary.total ?? 0}
                    </Badge>
                  )}
                  <Badge variant={run.run_id === activeRunId ? "default" : "secondary"}>
                    {run.run_id === activeRunId ? "Viewing" : "Details"}
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}

function ScientificMetricBadges({ metrics }: { metrics?: RunListItem["scientific_metrics"] | null }) {
  if (!metrics) {
    return null;
  }

  const blooms = metrics.pedagogical?.blooms_alignment;
  const retention = metrics.learning_outcomes?.predicted_retention;
  const cite = metrics.content_quality?.citation_validity;
  const entries = [
    blooms !== undefined && blooms !== null ? { label: "Bloom", value: blooms } : null,
    retention !== undefined && retention !== null ? { label: "Retention", value: retention } : null,
    cite !== undefined && cite !== null ? { label: "Citation", value: cite } : null,
  ].filter(Boolean) as { label: string; value: number }[];

  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {entries.map((entry) => (
        <Badge key={entry.label} variant="secondary" className="font-mono text-[11px]">
          {entry.label}: {formatPercent(entry.value)}
        </Badge>
      ))}
    </div>
  );
}

function formatPercent(value: number): string {
  if (Number.isFinite(value)) {
    return `${Math.round(value * 100)}%`;
  }
  return "n/a";
}

function AblationBadges({ ablations }: { ablations?: Record<string, boolean> | null }) {
  if (!ablations) {
    return null;
  }

  const flags = [
    { key: "use_world_model", label: "World model", short: "WM", enabled: ablations.use_world_model ?? true },
    { key: "use_students", label: "Students", short: "ST", enabled: ablations.use_students ?? true },
    { key: "allow_recursion", label: "Recursion", short: "RC", enabled: ablations.allow_recursion ?? true },
  ];

  return (
    <div className="mt-1 flex flex-wrap gap-2">
      {flags.map((flag) => (
        <Badge
          key={flag.key}
          variant={flag.enabled ? "success" : "destructive"}
          className="font-mono text-[11px]"
          title={`${flag.label}: ${flag.enabled ? "Enabled" : "Disabled"}`}
        >
          {flag.short}: {flag.enabled ? "On" : "Off"}
        </Badge>
      ))}
    </div>
  );
}

function ScienceConfigHint({ path }: { path?: string | null }) {
  if (!path) {
    return null;
  }

  return (
    <p className="mt-1 truncate text-[11px] font-mono text-muted-foreground" title={`Scientific config: ${path}`}>
      science cfg: {path}
    </p>
  );
}
