"use client";

import { useState, useEffect } from "react";
import {
  fetchGenerationResult,
  exportEvalSuite,
  type FullGenerationResult,
  type FailureModeResult,
} from "@/lib/api";
import EvaluatorPreviewCard from "@/components/export/EvaluatorPreviewCard";
import TestCaseGroup from "@/components/export/TestCaseGroup";

interface ExportStepProps {
  onStepComplete: (stepId: string) => void;
}

function Spinner({ size = "h-4 w-4" }: { size?: string }) {
  return (
    <svg
      className={`animate-spin ${size}`}
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

export default function ExportStep({ onStepComplete }: ExportStepProps) {
  const [result, setResult] = useState<FullGenerationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [evaluatorToggles, setEvaluatorToggles] = useState<
    Record<string, boolean>
  >({});
  const [testCaseToggles, setTestCaseToggles] = useState<
    Record<number, boolean>
  >({});
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Fetch generation result on mount
  useEffect(() => {
    let cancelled = false;

    fetchGenerationResult()
      .then((data) => {
        if (cancelled) return;

        if (data.status === "no_results") {
          setError(
            "No generation results available. Please go back and run generation first."
          );
          setLoading(false);
          return;
        }

        if (data.result) {
          const res = data.result;
          setResult(res);

          // Initialize all evaluator toggles to true (keyed by failure_mode_id)
          const evalToggles: Record<string, boolean> = {};
          for (const ev of res.evaluators) {
            evalToggles[ev.failure_mode_id] = true;
          }
          setEvaluatorToggles(evalToggles);

          // Initialize all test case toggles to true (keyed by array index)
          const tcToggles: Record<number, boolean> = {};
          res.test_cases.forEach((_, idx) => {
            tcToggles[idx] = true;
          });
          setTestCaseToggles(tcToggles);
        }

        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "Failed to load generation results";
        setError(message);
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Toggle an evaluator and auto-toggle its associated test cases
  const handleEvaluatorToggle = (failureModeId: string) => {
    const newValue = !evaluatorToggles[failureModeId];

    setEvaluatorToggles((prev) => ({
      ...prev,
      [failureModeId]: newValue,
    }));

    // Auto-toggle associated test cases
    if (result) {
      const updates: Record<number, boolean> = {};
      result.test_cases.forEach((tc, idx) => {
        if (tc.failure_mode_id === failureModeId) {
          updates[idx] = newValue;
        }
      });
      setTestCaseToggles((prev) => ({ ...prev, ...updates }));
    }
  };

  const handleTestCaseToggle = (index: number) => {
    setTestCaseToggles((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const handleToggleAllTestCasesForGroup = (
    failureModeId: string,
    enabled: boolean
  ) => {
    if (!result) return;
    const updates: Record<number, boolean> = {};
    result.test_cases.forEach((tc, idx) => {
      if (tc.failure_mode_id === failureModeId) {
        updates[idx] = enabled;
      }
    });
    setTestCaseToggles((prev) => ({ ...prev, ...updates }));
  };

  const handleSelectAllEvaluators = (enabled: boolean) => {
    if (!result) return;
    const updates: Record<string, boolean> = {};
    for (const ev of result.evaluators) {
      updates[ev.failure_mode_id] = enabled;
    }
    setEvaluatorToggles(updates);

    // Also toggle all test cases
    const tcUpdates: Record<number, boolean> = {};
    result.test_cases.forEach((_, idx) => {
      tcUpdates[idx] = enabled;
    });
    setTestCaseToggles(tcUpdates);
  };

  const handleExport = async () => {
    if (!result) return;
    setExporting(true);
    setExportError(null);

    try {
      const enabledEvaluatorIds = result.evaluators
        .filter((ev) => evaluatorToggles[ev.failure_mode_id])
        .map((ev) => ev.failure_mode_id);

      const enabledTestCaseIndices = result.test_cases
        .map((_, idx) => idx)
        .filter((idx) => testCaseToggles[idx]);

      const blob = await exportEvalSuite(enabledEvaluatorIds, enabledTestCaseIndices);

      // Trigger download
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "eval_suite.zip";
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Export failed. Please try again.";
      setExportError(message);
    } finally {
      setExporting(false);
    }
  };

  // Derived counts
  const totalEvaluators = result?.evaluators.length ?? 0;
  const totalTestCases = result?.test_cases.length ?? 0;
  const enabledEvaluatorCount = result?.evaluators.filter(
    (ev) => evaluatorToggles[ev.failure_mode_id]
  ).length ?? 0;
  const enabledTestCaseCount = result?.test_cases.filter(
    (_, idx) => testCaseToggles[idx]
  ).length ?? 0;

  const canExport = !exporting && (enabledEvaluatorCount > 0 || enabledTestCaseCount > 0);

  // --- Loading state ---
  if (loading) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center">
          <div
            className="flex items-center justify-center mb-3"
            style={{ color: "var(--color-accent)" }}
          >
            <Spinner size="h-6 w-6" />
          </div>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
            Loading generation results...
          </p>
        </div>
      </div>
    );
  }

  // --- Error state ---
  if (error) {
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
            {error}
          </div>
          <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            Go back to the Generate step and run generation first.
          </p>
        </div>
      </div>
    );
  }

  if (!result) return null;

  // Group test cases by failure_mode_id, preserving original indices
  const testCasesByFailureMode: Record<
    string,
    Array<{ input: string; expected_behavior: string; index: number }>
  > = {};
  result.test_cases.forEach((tc, idx) => {
    if (!testCasesByFailureMode[tc.failure_mode_id]) {
      testCasesByFailureMode[tc.failure_mode_id] = [];
    }
    testCasesByFailureMode[tc.failure_mode_id].push({ ...tc, index: idx });
  });

  const failureModeMap: Record<string, FailureModeResult> = {};
  for (const fm of result.failure_modes) {
    failureModeMap[fm.id] = fm;
  }

  const allEnabled =
    totalEvaluators > 0 && enabledEvaluatorCount === totalEvaluators;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-3xl mx-auto">

          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <h2
                className="text-xl font-semibold mb-1"
                style={{ color: "var(--color-text)" }}
              >
                Review &amp; Export
              </h2>
              <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                {enabledEvaluatorCount} of {totalEvaluators} evaluator
                {totalEvaluators !== 1 ? "s" : ""} selected,{" "}
                {enabledTestCaseCount} of {totalTestCases} test case
                {totalTestCases !== 1 ? "s" : ""} selected
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => handleSelectAllEvaluators(true)}
                disabled={allEnabled}
                className="text-xs cursor-pointer transition-opacity disabled:opacity-40 disabled:cursor-default"
                style={{ color: "var(--color-accent)" }}
              >
                Select all
              </button>
              <span style={{ color: "var(--color-border)" }}>|</span>
              <button
                onClick={() => handleSelectAllEvaluators(false)}
                disabled={enabledEvaluatorCount === 0}
                className="text-xs cursor-pointer transition-opacity disabled:opacity-40 disabled:cursor-default"
                style={{ color: "var(--color-accent)" }}
              >
                Deselect all
              </button>
            </div>
          </div>

          {/* Evaluators section */}
          <section className="mb-8">
            <h3
              className="text-sm font-semibold uppercase tracking-wide mb-3"
              style={{ color: "var(--color-text-muted)" }}
            >
              Evaluators ({enabledEvaluatorCount}/{totalEvaluators})
            </h3>
            <div className="flex flex-col gap-3">
              {result.evaluators.map((ev) => (
                <EvaluatorPreviewCard
                  key={ev.failure_mode_id}
                  evaluator={ev}
                  failureMode={failureModeMap[ev.failure_mode_id]}
                  enabled={evaluatorToggles[ev.failure_mode_id] ?? true}
                  onToggle={() => handleEvaluatorToggle(ev.failure_mode_id)}
                />
              ))}
            </div>
          </section>

          {/* Test cases section */}
          {Object.keys(testCasesByFailureMode).length > 0 && (
            <section className="mb-24">
              <h3
                className="text-sm font-semibold uppercase tracking-wide mb-3"
                style={{ color: "var(--color-text-muted)" }}
              >
                Test Cases ({enabledTestCaseCount}/{totalTestCases})
              </h3>
              <div className="flex flex-col gap-3">
                {result.evaluators.map((ev) => {
                  const group = testCasesByFailureMode[ev.failure_mode_id];
                  if (!group || group.length === 0) return null;
                  const fm = failureModeMap[ev.failure_mode_id];
                  return (
                    <TestCaseGroup
                      key={ev.failure_mode_id}
                      failureModeName={fm?.name ?? ev.failure_mode_id}
                      failureModeId={ev.failure_mode_id}
                      testCases={group}
                      toggles={testCaseToggles}
                      onToggle={handleTestCaseToggle}
                      onToggleAll={handleToggleAllTestCasesForGroup}
                    />
                  );
                })}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* Sticky export bar */}
      <div
        className="flex-shrink-0 px-8 py-4 flex items-center justify-between gap-4"
        style={{
          borderTop: "1px solid var(--color-border)",
          backgroundColor: "var(--color-bg)",
        }}
      >
        <div className="flex-1">
          {exportError && (
            <p className="text-xs" style={{ color: "#ef4444" }}>
              {exportError}
            </p>
          )}
        </div>
        <button
          onClick={handleExport}
          disabled={!canExport}
          className="flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            backgroundColor: "var(--color-accent)",
            color: "#ffffff",
          }}
          onMouseEnter={(e) => {
            if (canExport)
              e.currentTarget.style.backgroundColor =
                "var(--color-accent-muted)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "var(--color-accent)";
          }}
        >
          {exporting && <Spinner size="h-4 w-4" />}
          Export Eval Suite ({enabledEvaluatorCount} evaluator
          {enabledEvaluatorCount !== 1 ? "s" : ""},{" "}
          {enabledTestCaseCount} test case
          {enabledTestCaseCount !== 1 ? "s" : ""})
        </button>
      </div>
    </div>
  );
}
