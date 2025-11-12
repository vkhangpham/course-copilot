export type RunListItem = {
  run_id: string;
  manifest_path: string;
  created_at: string;
  has_course_plan: boolean;
  has_lecture: boolean;
  has_eval_report: boolean;
  overall_score?: number | null;
};

export type RunDetail = {
  run_id: string;
  manifest_path: string;
  created_at: string;
  manifest: Record<string, unknown>;
  dataset_summary?: Record<string, unknown> | null;
  ablations?: Record<string, boolean> | null;
  evaluation?: {
    overall_score?: number | null;
    rubrics?: { name: string; passed: boolean; score?: number | null }[];
  } | null;
  course_plan_excerpt?: string | null;
  lecture_excerpt?: string | null;
  notebook_slug?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_PORTAL_API_BASE ?? "http://localhost:8001";

async function handle<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const res = await fetch(input, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Portal API error (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function fetchRuns(): Promise<RunListItem[]> {
  return handle<RunListItem[]>(`${API_BASE}/runs`);
}

export async function fetchRunDetail(runId: string): Promise<RunDetail> {
  return handle<RunDetail>(`${API_BASE}/runs/${runId}`);
}
