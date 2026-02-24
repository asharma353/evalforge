"use client";

import { useState, useCallback } from "react";
import {
  triggerGeneration,
  type FailureModeResult,
  type EvaluatorResult,
} from "@/lib/api";
import { useSSE } from "@/lib/use-sse";
import EvaluatorList from "@/components/generation/EvaluatorList";

interface GenerateStepProps {
  onStepComplete: (stepId: string) => void;
  onStepData?: (stepId: string, data: unknown) => void;
  stepData?: Record<string, unknown>; // intent_model from questions step
}

type Phase = "idle" | "generating" | "complete" | "error";

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

export default function GenerateStep({
  onStepComplete,
  onStepData,
  stepData,
}: GenerateStepProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [failureModes, setFailureModes] = useState<FailureModeResult[]>([]);
  const [evaluators, setEvaluators] = useState<Record<string, EvaluatorResult>>({});
  const [testCaseCount, setTestCaseCount] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Listen for SSE generation events
  useSSE(
    "/api/sse",
    useCallback(
      (event: string, data: unknown) => {
        if (event === "generation_progress") {
          const d = data as {
            stage: string;
            failure_mode?: FailureModeResult;
            evaluator?: EvaluatorResult;
            test_case_count?: number;
          };

          if (d.stage === "failure_mode_found" && d.failure_mode) {
            setFailureModes((prev) => [...prev, d.failure_mode!]);
          } else if (d.stage === "evaluator_complete" && d.evaluator) {
            const ev = d.evaluator;
            setEvaluators((prev) => ({
              ...prev,
              [ev.failure_mode_id]: ev,
            }));
          } else if (d.stage === "test_data_complete") {
            setTestCaseCount(d.test_case_count ?? 0);
          }
        } else if (event === "generation_complete") {
          onStepData?.("generate", data);
          setPhase("complete");
        } else if (event === "generation_error") {
          const d = data as { error?: string };
          setError(d.error ?? "Generation failed");
          setPhase("error");
        }
      },
      [onStepData]
    )
  );

  const handleGenerate = async () => {
    if (!stepData) return;

    setPhase("generating");
    setError(null);
    setFailureModes([]);
    setEvaluators({});
    setTestCaseCount(0);

    try {
      await triggerGeneration(stepData);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to start generation";
      setError(message);
      setPhase("error");
    }
  };

  const handleRetry = () => {
    setPhase("idle");
    setError(null);
    setFailureModes([]);
    setEvaluators({});
    setTestCaseCount(0);
  };

  // --- Idle phase (no stepData: questions not completed) ---
  if (phase === "idle" && !stepData) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium mx-auto mb-4"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text-muted)",
            }}
          >
            4
          </div>
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--color-text)" }}
          >
            Generate Evaluators
          </h2>
          <p
            className="text-sm"
            style={{ color: "var(--color-text-muted)" }}
          >
            Complete the questions step first to enable eval generation.
          </p>
        </div>
      </div>
    );
  }

  // --- Idle phase (stepData present: ready to generate) ---
  if (phase === "idle" && stepData) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--color-text)" }}
          >
            Generate Evaluators
          </h2>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            Ready to generate binary evaluators and synthetic test data tailored to
            your application.
          </p>
          <button
            onClick={handleGenerate}
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
            Generate Evaluators
          </button>
        </div>
      </div>
    );
  }

  // --- Generating phase ---
  if (phase === "generating") {
    return (
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-1">
            <h2
              className="text-xl font-semibold"
              style={{ color: "var(--color-text)" }}
            >
              Generating Eval Framework
            </h2>
            <span style={{ color: "var(--color-accent)" }}>
              <Spinner size="h-5 w-5" />
            </span>
          </div>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            {failureModes.length} failure mode{failureModes.length !== 1 ? "s" : ""} found,{" "}
            {Object.keys(evaluators).length} evaluator{Object.keys(evaluators).length !== 1 ? "s" : ""} generated...
          </p>
          {failureModes.length > 0 && (
            <EvaluatorList failureModes={failureModes} evaluators={evaluators} />
          )}
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
            {error ?? "An unknown error occurred during generation."}
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
    <div className="flex-1 p-8 flex items-center justify-center">
      <div className="w-full max-w-md text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-lg mx-auto mb-4"
          style={{
            backgroundColor: "rgba(34, 197, 94, 0.1)",
            border: "1px solid rgba(34, 197, 94, 0.3)",
            color: "#22c55e",
          }}
        >
          &#10003;
        </div>
        <h2
          className="text-xl font-semibold mb-2"
          style={{ color: "var(--color-text)" }}
        >
          Eval Framework Generated
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-muted)" }}
        >
          {Object.keys(evaluators).length} evaluator{Object.keys(evaluators).length !== 1 ? "s" : ""},{" "}
          {testCaseCount} test case{testCaseCount !== 1 ? "s" : ""}
        </p>
        <button
          onClick={() => onStepComplete("generate")}
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
  );
}
