"use client";

import { useState, useEffect } from "react";
import {
  generateQuestions,
  submitAnswers,
  type AnalysisResult,
  type Question,
} from "@/lib/api";
import QuestionForm from "@/components/questions/QuestionForm";

interface QuestionsStepProps {
  onStepComplete: (stepId: string) => void;
  onStepData?: (stepId: string, data: unknown) => void;
  stepData?: AnalysisResult;
}

type Phase = "idle" | "generating" | "answering" | "submitting" | "complete" | "error";

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

export default function QuestionsStep({
  onStepComplete,
  onStepData,
  stepData,
}: QuestionsStepProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [skipped, setSkipped] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);

  // Auto-trigger question generation when stepData is available
  useEffect(() => {
    if (stepData && phase === "idle") {
      handleGenerate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepData]);

  const handleGenerate = async () => {
    if (!stepData) return;
    setPhase("generating");
    setError(null);

    try {
      const data = await generateQuestions(stepData);
      setQuestions(data.questions);

      // Pre-fill answers with defaults
      const defaultAnswers: Record<string, string | string[]> = {};
      for (const q of data.questions) {
        if (q.default !== undefined && q.default !== null) {
          defaultAnswers[q.id] = q.default;
        }
      }
      setAnswers(defaultAnswers);
      setPhase("answering");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to generate questions";
      setError(message);
      setPhase("error");
    }
  };

  const handleAnswerChange = (questionId: string, value: string | string[]) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
    // Remove from skipped if user starts answering
    setSkipped((prev) => prev.filter((id) => id !== questionId));
  };

  const handleSkip = (questionId: string) => {
    setSkipped((prev) =>
      prev.includes(questionId)
        ? prev.filter((id) => id !== questionId)
        : [...prev, questionId]
    );
  };

  const handleSubmit = async () => {
    if (!stepData) return;
    setPhase("submitting");
    setError(null);

    try {
      // Count answered (non-skipped) questions
      const answered = questions.filter((q) => !skipped.includes(q.id)).length;
      setAnsweredCount(answered);

      const data = await submitAnswers(stepData, answers, skipped);
      onStepData?.("questions", data.intent_model);
      setPhase("complete");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to submit answers";
      setError(message);
      setPhase("error");
    }
  };

  const handleSkipAll = async () => {
    if (!stepData) return;
    const allIds = questions.map((q) => q.id);
    setSkipped(allIds);
    setAnsweredCount(0);
    setPhase("submitting");
    setError(null);

    try {
      const data = await submitAnswers(stepData, answers, allIds);
      onStepData?.("questions", data.intent_model);
      setPhase("complete");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to submit answers";
      setError(message);
      setPhase("error");
    }
  };

  const handleRetry = () => {
    if (phase === "error" && questions.length > 0) {
      // If we already have questions, go back to answering
      setPhase("answering");
    } else {
      // Otherwise retry generation
      setPhase("idle");
      setQuestions([]);
      setAnswers({});
      setSkipped([]);
      handleGenerate();
    }
    setError(null);
  };

  // --- Idle phase (no stepData) ---
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
            3
          </div>
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--color-text)" }}
          >
            Guided Questions
          </h2>
          <p
            className="text-sm"
            style={{ color: "var(--color-text-muted)" }}
          >
            Complete the analysis step first to enable guided questioning.
          </p>
        </div>
      </div>
    );
  }

  // --- Generating phase ---
  if (phase === "generating" || (phase === "idle" && stepData)) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <div
            className="flex items-center justify-center gap-3 mb-4"
            style={{ color: "var(--color-accent)" }}
          >
            <Spinner size="h-6 w-6" />
          </div>
          <h2
            className="text-xl font-semibold mb-2"
            style={{ color: "var(--color-text)" }}
          >
            Generating Tailored Questions
          </h2>
          <p
            className="text-sm"
            style={{ color: "var(--color-text-muted)" }}
          >
            Analyzing your codebase to create targeted questions about your application...
          </p>
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
            {error ?? "An unknown error occurred."}
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
  if (phase === "complete") {
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
            Questionnaire Complete
          </h2>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            {answeredCount} question{answeredCount !== 1 ? "s" : ""} answered, {skipped.length} skipped
          </p>
          <button
            onClick={() => onStepComplete("questions")}
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

  // --- Answering / Submitting phase ---
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-2xl mx-auto">
        <h2
          className="text-xl font-semibold mb-1"
          style={{ color: "var(--color-text)" }}
        >
          Guided Questions
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-muted)" }}
        >
          Answer these questions to help us generate evaluators tailored to your application.
          You can skip any question to use the default value.
        </p>
        <QuestionForm
          questions={questions}
          answers={answers}
          skipped={skipped}
          onAnswerChange={handleAnswerChange}
          onSkip={handleSkip}
          onSubmit={handleSubmit}
          onSkipAll={handleSkipAll}
          isSubmitting={phase === "submitting"}
        />
      </div>
    </div>
  );
}
