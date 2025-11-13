export type ScientificMetricGroup = Record<string, number | null | undefined>;

export type ScientificMetrics = {
  pedagogical?: ScientificMetricGroup;
  content_quality?: ScientificMetricGroup;
  learning_outcomes?: ScientificMetricGroup;
  [key: string]: ScientificMetricGroup | undefined;
};

export type RunListItem = {
  run_id: string;
  manifest_path: string;
  created_at: string;
  has_course_plan: boolean;
  has_lecture: boolean;
  has_eval_report: boolean;
  overall_score?: number | null;
  highlight_source?: string | null;
  world_model_store_exists?: boolean | null;
  scientific_metrics?: ScientificMetrics | null;
  scientific_metrics_artifact?: string | null;
  science_config_path?: string | null;
  ablations?: Record<string, boolean> | null;
  notebook_export_summary?: {
    total?: number;
    success?: number;
    skipped?: number;
    errors?: number;
  } | null;
};

export type TraceFile = {
  name: string;
  label: string;
  path: string;
};

export type NotebookExportEntry = {
  title?: string | null;
  citations?: string[];
  status?: string | null;
  notebook?: string | null;
  note_id?: string | null;
  section_id?: string | null;
  path?: string | null;
  reason?: string | null;
  error?: string | null;
};

export type TeacherTraceMeta = {
  path: string;
  action_count: number;
  summary?: string | null;
  prompt?: string | null;
};

export type RunDetail = {
  run_id: string;
  manifest_path: string;
  created_at: string;
  manifest: Record<string, unknown>;
  dataset_summary?: Record<string, unknown> | null;
  ablations?: Record<string, boolean> | null;
  highlight_source?: string | null;
  world_model_store_exists?: boolean | null;
  scientific_metrics?: ScientificMetrics | null;
  scientific_metrics_artifact?: string | null;
  science_config_path?: string | null;
  evaluation?: {
    overall_score?: number | null;
    rubrics?: { name: string; passed: boolean; score?: number | null }[];
  } | null;
  course_plan_excerpt?: string | null;
  lecture_excerpt?: string | null;
  notebook_slug?: string | null;
  notebook_exports?: NotebookExportEntry[] | null;
  evaluation_attempts?: {
    iteration: number;
    overall_score?: number | null;
    quiz_pass_rate?: number | null;
    failing_rubrics?: string[];
    failing_questions?: string[];
  }[] | null;
  trace_files?: TraceFile[] | null;
  teacher_trace?: TeacherTraceMeta | null;
  notebook_export_summary?: {
    total?: number;
    success?: number;
    skipped?: number;
    errors?: number;
  } | null;
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

export async function fetchNotebookExports(runId: string): Promise<NotebookExportEntry[]> {
  return handle<NotebookExportEntry[]>(`${API_BASE}/runs/${runId}/notebook-exports`);
}

export async function fetchLatestRun(): Promise<RunDetail> {
  return handle<RunDetail>(`${API_BASE}/runs/latest`);
}
