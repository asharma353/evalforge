"use client";

interface AnalysisProgressProps {
  stage: string;
  current: number;
  total: number;
  detail: string;
}

function CheckIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function getStageLabel(stage: string): string {
  if (stage === "parsing") return "Parsing files...";
  if (stage === "analyzing") return "Analyzing call sites...";
  if (stage === "complete") return "Analysis complete";
  return stage;
}

export default function AnalysisProgress({
  stage,
  current,
  total,
  detail,
}: AnalysisProgressProps) {
  const percentage = total > 0 ? Math.min((current / total) * 100, 100) : 0;
  const isComplete = stage === "complete";

  return (
    <div
      className="rounded-md p-4 mb-6"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Stage label and completion indicator */}
      <div className="flex items-center gap-2 mb-3">
        {isComplete ? (
          <span style={{ color: "var(--color-accent)" }}>
            <CheckIcon />
          </span>
        ) : (
          <div
            className="w-4 h-4 rounded-full border-2 animate-spin"
            style={{
              borderColor: "var(--color-border)",
              borderTopColor: "var(--color-accent)",
            }}
          />
        )}
        <span
          className="text-sm font-medium"
          style={{ color: "var(--color-text)" }}
        >
          {getStageLabel(stage)}
        </span>

        {/* Current/total counter */}
        {!isComplete && total > 0 && (
          <span
            className="ml-auto text-xs font-mono"
            style={{ color: "var(--color-text-muted)" }}
          >
            {current} / {total}
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div
        className="w-full rounded-full overflow-hidden mb-2"
        style={{
          backgroundColor: "var(--color-bg)",
          height: "6px",
        }}
      >
        <div
          style={{
            width: `${isComplete ? 100 : percentage}%`,
            height: "100%",
            backgroundColor: "var(--color-accent)",
            transition: "width 0.3s ease",
            borderRadius: "9999px",
          }}
        />
      </div>

      {/* Detail text */}
      {detail && !isComplete && (
        <div
          className="text-xs font-mono truncate mt-1"
          style={{ color: "var(--color-text-muted)" }}
        >
          {detail}
        </div>
      )}
    </div>
  );
}
