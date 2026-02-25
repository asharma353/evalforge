"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { FailureModeResult, FullEvaluatorResult } from "@/lib/api";

const SEVERITY_STYLES: Record<
  string,
  { backgroundColor: string; color: string; border: string }
> = {
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

const EVALUATOR_TYPE_STYLES: Record<
  string,
  { backgroundColor: string; color: string; border: string }
> = {
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

interface EvaluatorPreviewCardProps {
  evaluator: FullEvaluatorResult;
  failureMode: FailureModeResult | undefined;
  enabled: boolean;
  onToggle: () => void;
}

export default function EvaluatorPreviewCard({
  evaluator,
  failureMode,
  enabled,
  onToggle,
}: EvaluatorPreviewCardProps) {
  const [codeExpanded, setCodeExpanded] = useState(false);

  const severity = failureMode?.severity ?? "low";
  const evaluatorType = evaluator.evaluator_type;
  const displayName = failureMode?.name ?? evaluator.filename;

  const severityStyle = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.low;
  const typeStyle =
    EVALUATOR_TYPE_STYLES[evaluatorType] ?? EVALUATOR_TYPE_STYLES.assertion;

  return (
    <div
      className="rounded-md p-4"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        opacity: enabled ? 1 : 0.5,
        transition: "opacity 0.15s ease",
      }}
    >
      {/* Header: checkbox + name + badges */}
      <div className="flex items-start gap-3 mb-2">
        <input
          type="checkbox"
          checked={enabled}
          onChange={onToggle}
          className="mt-0.5 flex-shrink-0 cursor-pointer"
          style={{ accentColor: "var(--color-accent)" }}
        />
        <div className="flex-1 flex items-start justify-between gap-3 min-w-0">
          <span
            className="text-sm font-medium truncate"
            style={{ color: "var(--color-text)" }}
          >
            {displayName}
          </span>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span
              className="text-xs px-2 py-0.5 rounded font-medium"
              style={severityStyle}
            >
              {severity}
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded font-medium"
              style={typeStyle}
            >
              {evaluatorType}
            </span>
          </div>
        </div>
      </div>

      {/* Description */}
      <p
        className="text-xs mb-2 ml-6"
        style={{ color: "var(--color-text-muted)" }}
      >
        {evaluator.description}
      </p>

      {/* Filename */}
      <div className="ml-6 mb-2">
        <span
          className="text-xs font-mono"
          style={{ color: "var(--color-text-muted)" }}
        >
          {evaluator.filename}
        </span>
      </div>

      {/* Code preview toggle */}
      <div className="ml-6">
        <button
          onClick={() => setCodeExpanded((prev) => !prev)}
          className="text-xs cursor-pointer transition-colors"
          style={{ color: "var(--color-accent)" }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.opacity = "0.7")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.opacity = "1")
          }
        >
          {codeExpanded ? "Hide code" : "Show code"}
        </button>

        {codeExpanded && (
          <div
            className="mt-2 rounded overflow-hidden text-xs"
            style={{ border: "1px solid var(--color-border)" }}
          >
            <SyntaxHighlighter
              language="python"
              style={vscDarkPlus}
              customStyle={{ margin: 0, fontSize: "0.75rem", maxHeight: "300px" }}
            >
              {evaluator.code}
            </SyntaxHighlighter>
          </div>
        )}
      </div>
    </div>
  );
}
