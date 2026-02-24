"use client";

import { useState, useCallback } from "react";
import { analyzeProject, type AnalysisResult } from "@/lib/api";
import { useSSE } from "@/lib/use-sse";
import AnalysisProgress from "@/components/analysis/AnalysisProgress";
import AppTypeClassifier from "@/components/analysis/AppTypeClassifier";
import CallSiteList from "@/components/analysis/CallSiteList";

interface UploadStepData {
  projectPath: string;
  filePaths: string[];
}

interface AnalyzeStepProps {
  onStepComplete: (stepId: string) => void;
  stepData?: UploadStepData;
}

interface ProgressState {
  stage: string;
  current: number;
  total: number;
  detail: string;
}

type Phase = "idle" | "analyzing" | "complete" | "error";

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        className="opacity-25"
      />
      <path
        d="M12 2C6.47715 2 2 12 6.47715 12"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        className="opacity-75"
      />
    </svg>
  );
}

export default function AnalyzeStep({
  onStepComplete,
  stepData,
}: AnalyzeStepProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState<ProgressState>({
    stage: "parsing",
    current: 0,
    total: 0,
    detail: "",
  });
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [appTypeOverride, setAppTypeOverride] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Listen for SSE analysis events
  useSSE(
    "/api/sse",
    useCallback(
      (event: string, data: unknown) => {
        if (event === "analysis_progress") {
          const d = data as { stage: string; current: number; total: number; detail: string };
          setProgress({
            stage: d.stage ?? "parsing",
            current: d.current ?? 0,
            total: d.total ?? 0,
            detail: d.detail ?? "",
          });
        } else if (event === "analysis_complete") {
          const d = data as AnalysisResult;
          setResult(d);
          setPhase("complete");
          setProgress((prev) => ({ ...prev, stage: "complete" }));
        } else if (event === "analysis_error") {
          const d = data as { message: string };
          setError(d.message ?? "Analysis failed");
          setPhase("error");
        }
      },
      []
    )
  );

  const handleStartAnalysis = async () => {
    if (!stepData?.projectPath) {
      setError("No project path available. Please complete the upload step first.");
      setPhase("error");
      return;
    }

    setPhase("analyzing");
    setError(null);
    setProgress({ stage: "parsing", current: 0, total: 0, detail: "" });

    try {
      await analyzeProject(stepData.projectPath, stepData.filePaths ?? []);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
      setPhase("error");
    }
  };

  const handleRetry = () => {
    setPhase("idle");
    setError(null);
    setResult(null);
    setAppTypeOverride(null);
  };

  // Determine displayed app type (override takes precedence)
  const displayedAppType =
    result && appTypeOverride
      ? { ...result.app_type, type: appTypeOverride }
      : result?.app_type;

  // --- Idle phase ---
  if (phase === "idle") {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium mx-auto mb-4"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-accent)",
            }}
          >
            2
          </div>
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--color-text)" }}
          >
            Analyze Codebase
          </h2>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            Scan your project for LLM API calls, extract prompts, and classify
            the application type. This may take a moment for larger codebases.
          </p>
          <button
            onClick={handleStartAnalysis}
            className="px-6 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer"
            style={{
              backgroundColor: "var(--color-accent)",
              color: "#ffffff",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.backgroundColor = "var(--color-accent-muted)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.backgroundColor = "var(--color-accent)")
            }
          >
            Start Analysis
          </button>
        </div>
      </div>
    );
  }

  // --- Analyzing phase ---
  if (phase === "analyzing") {
    return (
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          <h2
            className="text-xl font-semibold mb-1"
            style={{ color: "var(--color-text)" }}
          >
            Analyzing Codebase
          </h2>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            Scanning for LLM API calls and extracting prompts...
          </p>
          <AnalysisProgress
            stage={progress.stage}
            current={progress.current}
            total={progress.total}
            detail={progress.detail}
          />
          <div
            className="flex items-center gap-2 text-sm"
            style={{ color: "var(--color-text-muted)" }}
          >
            <Spinner />
            <span>Streaming analysis results in real time...</span>
          </div>
        </div>
      </div>
    );
  }

  // --- Error phase ---
  if (phase === "error") {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <div
            className="rounded-md px-4 py-3 mb-6 text-sm"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#ef4444",
            }}
          >
            {error ?? "An unknown error occurred during analysis."}
          </div>
          <button
            onClick={handleRetry}
            className="px-6 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-accent)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // --- Complete phase ---
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-2xl mx-auto">
        <h2
          className="text-xl font-semibold mb-1"
          style={{ color: "var(--color-text)" }}
        >
          Analysis Results
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-muted)" }}
        >
          {result?.summary.total_files_analyzed ?? 0} files analyzed &mdash;{" "}
          {result?.summary.total_call_sites ?? 0} LLM call sites detected
        </p>

        {/* Progress in complete state */}
        <AnalysisProgress
          stage="complete"
          current={result?.summary.total_files_analyzed ?? 0}
          total={result?.summary.total_files_analyzed ?? 0}
          detail=""
        />

        {/* App type classifier */}
        {displayedAppType && (
          <AppTypeClassifier
            appType={displayedAppType}
            onOverride={setAppTypeOverride}
          />
        )}

        {/* Call site list */}
        <div
          className="text-xs font-medium uppercase tracking-wider mb-3"
          style={{ color: "var(--color-text-muted)" }}
        >
          Call Sites
        </div>
        <CallSiteList callSites={result?.call_sites ?? []} />

        {/* Continue button */}
        <div className="mt-6">
          <button
            onClick={() => onStepComplete("analyze")}
            className="px-6 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer"
            style={{
              backgroundColor: "var(--color-accent)",
              color: "#ffffff",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.backgroundColor = "var(--color-accent-muted)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.backgroundColor = "var(--color-accent)")
            }
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
