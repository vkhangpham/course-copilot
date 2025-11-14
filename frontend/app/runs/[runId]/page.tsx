import Link from "next/link";

import { RunDetailSection } from "@/components/run-detail-section";
import { RunHistory } from "@/components/run-history";
import { Button } from "@/components/ui/button";
import { fetchRunDetail, fetchRuns } from "@/lib/api";

async function safeFetchRunDetail(runId: string) {
  try {
    return await fetchRunDetail(runId);
  } catch (error) {
    console.warn("Portal: unable to load run", runId, error);
    return null;
  }
}

export default async function RunDetailPage({ params }: { params: { runId: string } }) {
  const [runsResult, detailResult] = await Promise.allSettled([fetchRuns(), safeFetchRunDetail(params.runId)]);
  const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
  const detail = detailResult.status === "fulfilled" ? detailResult.value : null;

  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="absolute inset-x-0 top-0 -z-10 flex justify-center">
        <div className="h-[320px] w-[480px] rounded-full bg-indigo-200/40 blur-[120px]" />
      </div>
      {detail ? (
        <RunDetailSection detail={detail} />
      ) : (
        <section className="mx-auto w-full max-w-3xl px-6 py-24 text-center">
          <h1 className="text-3xl font-bold text-slate-900">Run not found</h1>
          <p className="mt-3 text-sm text-muted-foreground">
            We couldn&apos;t find run <span className="font-mono">{params.runId}</span>. It may have been deleted or the
            manifest has not been generated yet.
          </p>
          <div className="mt-6 flex justify-center">
            <Button asChild>
              <Link href="/">Back to latest run</Link>
            </Button>
          </div>
        </section>
      )}
      <RunHistory runs={runs} activeRunId={detail?.run_id ?? params.runId} />
    </main>
  );
}
