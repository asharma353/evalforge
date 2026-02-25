"use client";

interface TestCaseItem {
  input: string;
  expected_behavior: string;
  index: number;
}

interface TestCaseGroupProps {
  failureModeName: string;
  failureModeId: string;
  testCases: TestCaseItem[];
  toggles: Record<number, boolean>;
  onToggle: (index: number) => void;
  onToggleAll: (failureModeId: string, enabled: boolean) => void;
}

export default function TestCaseGroup({
  failureModeName,
  failureModeId,
  testCases,
  toggles,
  onToggle,
  onToggleAll,
}: TestCaseGroupProps) {
  const allEnabled = testCases.every((tc) => toggles[tc.index] !== false);
  const someEnabled = testCases.some((tc) => toggles[tc.index] !== false);

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Group header */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{
          backgroundColor: "var(--color-surface)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <span
          className="text-sm font-medium"
          style={{ color: "var(--color-text)" }}
        >
          {failureModeName}
          <span
            className="ml-2 text-xs font-normal"
            style={{ color: "var(--color-text-muted)" }}
          >
            ({testCases.filter((tc) => toggles[tc.index] !== false).length}/{testCases.length} selected)
          </span>
        </span>
        <button
          onClick={() => onToggleAll(failureModeId, !allEnabled || !someEnabled ? true : false)}
          className="text-xs cursor-pointer transition-opacity"
          style={{ color: "var(--color-accent)" }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.7")}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
        >
          {allEnabled ? "Deselect all" : "Select all"}
        </button>
      </div>

      {/* Test case rows */}
      <div>
        {testCases.map((tc, i) => {
          const enabled = toggles[tc.index] !== false;
          const truncatedInput =
            tc.input.length > 80 ? tc.input.slice(0, 80) + "..." : tc.input;

          return (
            <div
              key={tc.index}
              className="flex items-start gap-3 px-4 py-2.5"
              style={{
                borderTop: i > 0 ? "1px solid var(--color-border)" : undefined,
                backgroundColor:
                  i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                opacity: enabled ? 1 : 0.45,
                transition: "opacity 0.15s ease",
              }}
            >
              <input
                type="checkbox"
                checked={enabled}
                onChange={() => onToggle(tc.index)}
                className="mt-0.5 flex-shrink-0 cursor-pointer"
                style={{ accentColor: "var(--color-accent)" }}
              />
              <div className="flex-1 min-w-0">
                <p
                  className="text-xs font-mono truncate mb-0.5"
                  style={{ color: "var(--color-text)" }}
                  title={tc.input}
                >
                  {truncatedInput}
                </p>
                <p
                  className="text-xs"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  {tc.expected_behavior}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
