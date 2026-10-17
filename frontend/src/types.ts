export type Challenge = {
  id: string;
  title: string;
  category: string;
  description: string;
  specification: string;
  constraints: string;
  complexity: string;
  reference: string;
  buggy: string;
  test_count: number;
  examples: { input: unknown; expected: unknown }[];
};
export type CaseResult = {
  name: string;
  hidden: boolean;
  status: string;
  input: unknown;
  expected: unknown;
  actual: unknown;
  error: string | null;
  duration_ms: number | null;
  reference_duration_ms: number | null;
  peak_rss_kib: number | null;
};
export type Result = {
  mode: string;
  cases: CaseResult[];
  passed: number;
  total: number;
  pass_rate: number;
  categories: string[];
  static_findings: {
    code: string;
    message: string;
    location: { row: number; column: number };
  }[];
  static_status: string;
  execution_ms: number;
  summary: string;
  reference_verified: boolean;
  candidate_sha256: string;
  runtime: string;
};
export type Submission = {
  id: string;
  challenge_id: string;
  label: string;
  origin: string;
  created_at: string;
  passed: number;
  total: number;
  pass_rate: number;
  mode: string;
  execution_ms: number;
  code?: string;
  result?: Result;
};
export type Stats = {
  submissions: number;
  fully_passing: number;
  tests_passed: number;
  tests_run: number;
  average_execution_ms: number | null;
};
export type Capability = {
  mode: string;
  arbitrary_code_enabled: boolean;
  message: string;
};
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, init);
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  }
  return response.json();
}
