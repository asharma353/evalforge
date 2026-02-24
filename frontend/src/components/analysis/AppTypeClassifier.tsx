"use client";

export interface AppTypeInfo {
  type: string;
  confidence: number;
  signals: string[];
}

interface AppTypeClassifierProps {
  appType: AppTypeInfo;
  onOverride: (type: string) => void;
}

const APP_TYPE_OPTIONS = [
  { value: "rag", label: "RAG (Retrieval-Augmented Generation)" },
  { value: "agent", label: "Agent" },
  { value: "chatbot", label: "Chatbot" },
  { value: "document_processing", label: "Document Processing" },
  { value: "general", label: "General" },
];

function formatAppType(type: string): string {
  const option = APP_TYPE_OPTIONS.find((o) => o.value === type);
  return option ? option.label : type;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  let color = "#22c55e"; // green
  if (pct < 50) color = "#ef4444"; // red
  else if (pct < 75) color = "#f59e0b"; // amber

  return (
    <span
      className="text-xs font-medium px-2 py-0.5 rounded-full"
      style={{
        backgroundColor: `${color}22`,
        color: color,
      }}
    >
      {pct}% confidence
    </span>
  );
}

export default function AppTypeClassifier({
  appType,
  onOverride,
}: AppTypeClassifierProps) {
  return (
    <div
      className="rounded-md p-4 mb-6"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div
        className="text-xs font-medium uppercase tracking-wider mb-3"
        style={{ color: "var(--color-text-muted)" }}
      >
        App Type Classification
      </div>

      {/* Current classification */}
      <div className="flex items-center gap-3 mb-3">
        <span
          className="text-sm font-semibold"
          style={{ color: "var(--color-text)" }}
        >
          {formatAppType(appType.type)}
        </span>
        <ConfidenceBadge confidence={appType.confidence} />
      </div>

      {/* Override dropdown */}
      <div className="mb-3">
        <label
          className="block text-xs mb-1.5"
          style={{ color: "var(--color-text-muted)" }}
        >
          Override classification:
        </label>
        <select
          value={appType.type}
          onChange={(e) => onOverride(e.target.value)}
          className="w-full rounded-md px-3 py-2 text-sm outline-none"
          style={{
            backgroundColor: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
            cursor: "pointer",
          }}
        >
          {APP_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Signals */}
      {appType.signals.length > 0 && (
        <div>
          <div
            className="text-xs mb-1.5"
            style={{ color: "var(--color-text-muted)" }}
          >
            Detection signals:
          </div>
          <ul className="space-y-0.5">
            {appType.signals.map((signal, index) => (
              <li
                key={index}
                className="text-xs flex items-start gap-1.5"
                style={{ color: "var(--color-text-muted)" }}
              >
                <span style={{ color: "var(--color-accent)", marginTop: "2px" }}>
                  •
                </span>
                {signal}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
