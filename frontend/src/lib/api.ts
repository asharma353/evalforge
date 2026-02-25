// API client for backend communication

export interface PromptInfo {
  role: string;
  content: string;
  is_dynamic: boolean;
}

export interface CallSiteInfo {
  file_path: string;
  framework: string;
  method: string;
  start_line: number;
  end_line: number;
  source: string;
  is_test: boolean;
  prompts: PromptInfo[];
}

export interface AppTypeInfo {
  type: string;
  confidence: number;
  signals: string[];
}

export interface AnalysisSummary {
  total_files_analyzed: number;
  files_with_calls: number;
  total_call_sites: number;
}

export interface AnalysisResult {
  call_sites: CallSiteInfo[];
  app_type: AppTypeInfo;
  summary: AnalysisSummary;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  children: FileNode[] | null;
  extension: string | null;
}

export interface ScanResponse {
  project_name: string;
  root_path: string;
  file_tree: FileNode[];
  total_files: number;
  supported_files: number;
}

/**
 * Scan a project directory for supported files.
 * POST /api/projects/scan with project_name and path.
 */
export async function scanProject(
  projectName: string,
  path: string
): Promise<ScanResponse> {
  const response = await fetch("/api/projects/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_name: projectName, path }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const message =
      errorData?.detail || `Scan failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}

/**
 * Trigger analysis of an already-scanned project.
 * POST /api/projects/analyze -- returns 202; actual results come via SSE.
 */
export async function analyzeProject(
  projectPath: string,
  filePaths: string[]
): Promise<void> {
  const response = await fetch("/api/projects/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_path: projectPath, file_paths: filePaths }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Analysis failed with status ${response.status}`
    );
  }
  // Response is 202 - actual results come via SSE
}

// --- Question types and endpoints ---

export interface QuestionOption {
  value: string;
  label: string;
}

export interface Question {
  id: string;
  text: string;
  category: string;
  type: string;
  options: QuestionOption[] | null;
  default: string | string[];
  placeholder: string | null;
  context_hint: string | null;
}

export interface GenerateQuestionsResponse {
  questions: Question[];
  generation_source: string;
}

export interface IntentModelResponse {
  intent_model: Record<string, unknown>;
}

/**
 * Generate tailored questions based on analysis results.
 * POST /api/projects/questions/generate
 */
export async function generateQuestions(
  analysisResult: AnalysisResult
): Promise<GenerateQuestionsResponse> {
  const response = await fetch("/api/projects/questions/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysis_result: analysisResult }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Question generation failed with status ${response.status}`
    );
  }

  return response.json();
}

/**
 * Submit question answers and get the intent model.
 * POST /api/projects/questions/submit
 */
export async function submitAnswers(
  analysisResult: AnalysisResult,
  answers: Record<string, string | string[]>,
  skipped: string[]
): Promise<IntentModelResponse> {
  const response = await fetch("/api/projects/questions/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      analysis_result: analysisResult,
      answers,
      skipped,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Answer submission failed with status ${response.status}`
    );
  }

  return response.json();
}

// --- Generation types and endpoints ---

export interface FailureModeResult {
  id: string;
  name: string;
  description: string;
  evaluator_type: "assertion" | "regex" | "llm_judge";
  app_type: string;
  severity: "high" | "medium" | "low";
}

export interface EvaluatorResult {
  failure_mode_id: string;
  filename: string;
  evaluator_type: "assertion" | "regex" | "llm_judge";
  description: string;
}

export interface GenerationSummary {
  failure_mode_count: number;
  evaluator_count: number;
  test_case_count: number;
}

/**
 * Trigger eval and test data generation from an intent model.
 * POST /api/projects/generate -- returns 202; actual results come via SSE.
 */
export async function triggerGeneration(
  intentModel: Record<string, unknown>
): Promise<void> {
  const response = await fetch("/api/projects/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent_model: intentModel }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Generation failed with status ${response.status}`
    );
  }
  // 202 accepted - actual results come via SSE
}

// --- Export types and endpoints ---

export interface FullEvaluatorResult {
  failure_mode_id: string;
  filename: string;
  evaluator_type: "assertion" | "regex" | "llm_judge";
  code: string;
  description: string;
}

export interface FullTestCase {
  input: string;
  expected_behavior: string;
  failure_mode_id: string;
}

export interface FullGenerationResult {
  failure_modes: FailureModeResult[];
  evaluators: FullEvaluatorResult[];
  test_cases: FullTestCase[];
  generation_source: string;
}

/**
 * Fetch the full generation result including evaluator code and test cases.
 * GET /api/projects/generate/result
 */
export async function fetchGenerationResult(): Promise<{
  status: string;
  result?: FullGenerationResult;
  message?: string;
}> {
  const response = await fetch("/api/projects/generate/result");

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch result with status ${response.status}`
    );
  }

  return response.json();
}

/**
 * Export a customized eval suite as a zip file.
 * POST /api/projects/export with selection filter; returns Blob.
 */
export async function exportEvalSuite(
  enabledEvaluatorIds: string[],
  enabledTestCaseIndices: number[]
): Promise<Blob> {
  const response = await fetch("/api/projects/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      enabled_evaluator_ids: enabledEvaluatorIds,
      enabled_test_case_indices: enabledTestCaseIndices,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Export failed with status ${response.status}`
    );
  }

  return response.blob();
}
