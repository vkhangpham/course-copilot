import { RunDetailSection } from "@/components/run-detail-section";
import { RunHistory } from "@/components/run-history";
import { fetchLatestRun, fetchRuns } from "@/lib/api";

async function loadData() {
  try {
    const [runsResult, detailResult] = await Promise.allSettled([fetchRuns(), fetchLatestRun()]);
    const runs = runsResult.status === "fulfilled" ? runsResult.value : [];
    const detail = detailResult.status === "fulfilled" ? detailResult.value : null;
    return { runs, detail };
  } catch (error) {
    console.warn("Portal backend unavailable", error);
    return { runs: [], detail: null };
  }
}

export default async function Page() {
  const { runs, detail } = await loadData();
  return (
    <main className="relative min-h-screen overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="absolute inset-x-0 top-0 -z-10 flex justify-center">
        <div className="h-[320px] w-[480px] rounded-full bg-sky-200/40 blur-[120px]" />
      </div>
      <RunDetailSection detail={detail} />
      <RunHistory runs={runs} activeRunId={detail?.run_id} />
    </main>
  );
}
