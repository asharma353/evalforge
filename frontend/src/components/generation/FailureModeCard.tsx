"use client";

import type { FailureModeResult, EvaluatorResult } from "@/lib/api";

interface FailureModeCardProps {
  failureMode: FailureModeResult;
  evaluator?: EvaluatorResult | null;
}

function Spinner() {
  return (
    <svg
      className="animate-spin h-3 w-3"
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

const SEVERITY_STYLES: Record<string, { backgroundColor: string; color: string; border: string }> = {
  high: {
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    color: "#ef4444",
    border: "1px solid rgba(239, 68, 68, 0.3)",
  },
  medium: {
    backgroundColor: "rgba(245, 158, 11, 0.1)",
    color: "#f59e0b",
    border: "1px solid rgba(245, 158, 11, 0.3)",
  },
  low: {
    backgroundColor: "rgba(107, 114, 128, 0.1)",
    color: "#6b7280",
    border: "1px solid rgba(107, 114, 128, 0.3)",
  },
};

const EVALUATOR_TYPE_STYLES: Record<string, { backgroundColor: string; color: string; border: string }> = {
  assertion: {
    backgroundColor: "rgba(59, 130, 246, 0.1)",
    color: "#3b82f6",
    border: "1px solid rgba(59, 130, 246, 0.3)",
  },
  regex: {
    backgroundColor: "rgba(168, 85, 247, 0.1)",
    color: "#a855f7",
    border: "1px solid rgba(168, 85, 247, 0.3)",
  },
  llm_judge: {
    backgroundColor: "rgba(249, 115, 22, 0.1)",
    color: "#f97316",
    border: "1px solid rgba(249, 115, 22, 0.3)",
  },
};

export default function FailureModeCard({ failureMode, evaluator }: FailureModeCardProps) {
  const severityStyle = SEVERITY_STYLES[failureMode.severity] ?? SEVERITY_STYLES.low;
  const evaluatorTypeStyle =
    EVALUATOR_TYPE_STYLES[failureMode.evaluator_type] ?? EVALUATOR_TYPE_STYLES.assertion;

  return (
    <div
      className="rounded-md p-4"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Header: name + badges */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <span
          className="text-sm font-medium"
          style={{ color: "var(--color-text)" }}
        >
          {failureMode.name}
        </span>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Severity badge */}
          <span
            className="text-xs px-2 py-0.5 rounded font-medium"
            style={severityStyle}
          >
            {failureMode.severity}
          </span>
          {/* Evaluator type badge */}
          <span
            className="text-xs px-2 py-0.5 rounded font-medium"
            style={evaluatorTypeStyle}
          >
            {failureMode.evaluator_type}
          </span>
        </div>
      </div>

      {/* Description */}
      <p
        className="text-xs mb-3"
        style={{ color: "var(--color-text-muted)" }}
      >
        {failureMode.description}
      </p>

      {/* Evaluator row */}
      {evaluator ? (
        <div
          className="flex items-center gap-2 text-xs pt-2"
          style={{ borderTop: "1px solid var(--color-border)" }}
        >
          <span
            className="font-mono"
            style={{ color: "var(--color-text)" }}
          >
            {evaluator.filename}
          </span>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: "rgba(34, 197, 94, 0.1)",
              color: "#22c55e",
              border: "1px solid rgba(34, 197, 94, 0.3)",
            }}
          >
            ready
          </span>
        </div>
      ) : (
        <div
          className="flex items-center gap-2 text-xs pt-2"
          style={{ borderTop: "1px solid var(--color-border)", color: "var(--color-text-muted)" }}
        >
          <Spinner />
          <span>Generating evaluator...</span>
        </div>
      )}
    </div>
  );
}
