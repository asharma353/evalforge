"use client";

import { useState, useMemo } from "react";
import type { Question } from "@/lib/api";
import QuestionCard from "./QuestionCard";

interface QuestionFormProps {
  questions: Question[];
  answers: Record<string, string | string[]>;
  skipped: string[];
  onAnswerChange: (questionId: string, value: string | string[]) => void;
  onSkip: (questionId: string) => void;
  onSubmit: () => void;
  onSkipAll: () => void;
  isSubmitting: boolean;
}

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

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

export default function QuestionForm({
  questions,
  answers,
  skipped,
  onAnswerChange,
  onSkip,
  onSubmit,
  onSkipAll,
  isSubmitting,
}: QuestionFormProps) {
  const [submitHover, setSubmitHover] = useState(false);
  const [skipAllHover, setSkipAllHover] = useState(false);

  // Group questions by category
  const groupedQuestions = useMemo(() => {
    const groups: { category: string; questions: Question[] }[] = [];
    const seen = new Set<string>();

    for (const q of questions) {
      if (!seen.has(q.category)) {
        seen.add(q.category);
        groups.push({ category: q.category, questions: [] });
      }
      const group = groups.find((g) => g.category === q.category);
      group?.questions.push(q);
    }

    return groups;
  }, [questions]);

  const answeredCount = questions.filter((q) => !skipped.includes(q.id)).length;

  return (
    <div>
      {/* Progress indicator */}
      <div
        className="flex items-center justify-between text-xs mb-4 px-1"
        style={{ color: "var(--color-text-muted)" }}
      >
        <span>
          {questions.length} question{questions.length !== 1 ? "s" : ""} &mdash;{" "}
          {answeredCount} to answer, {skipped.length} skipped
        </span>
      </div>

      {/* Question groups */}
      {groupedQuestions.map((group) => (
        <div key={group.category} className="mb-6">
          <div
            className="text-xs font-medium uppercase tracking-wider mb-3 px-1"
            style={{
              color: "var(--color-text-muted)",
              borderBottom: "1px solid var(--color-border)",
              paddingBottom: "0.5rem",
            }}
          >
            {formatCategory(group.category)}
          </div>
          {group.questions.map((q) => (
            <QuestionCard
              key={q.id}
              question={q}
              value={answers[q.id] ?? q.default ?? ""}
              onChange={onAnswerChange}
              onSkip={onSkip}
              isSkipped={skipped.includes(q.id)}
            />
          ))}
        </div>
      ))}

      {/* Action bar */}
      <div
        className="flex items-center justify-between gap-4 mt-6 pt-4"
        style={{ borderTop: "1px solid var(--color-border)" }}
      >
        <button
          onClick={onSkipAll}
          disabled={isSubmitting}
          className="px-4 py-2.5 rounded-md text-sm font-medium transition-colors cursor-pointer"
          style={{
            backgroundColor: skipAllHover
              ? "var(--color-surface)"
              : "transparent",
            border: "1px solid var(--color-border)",
            color: "var(--color-text-muted)",
            opacity: isSubmitting ? 0.5 : 1,
            cursor: isSubmitting ? "not-allowed" : "pointer",
          }}
          onMouseEnter={() => setSkipAllHover(true)}
          onMouseLeave={() => setSkipAllHover(false)}
        >
          Skip All &amp; Use Defaults
        </button>
        <button
          onClick={onSubmit}
          disabled={isSubmitting}
          className="px-6 py-2.5 rounded-md text-sm font-medium transition-colors flex items-center gap-2"
          style={{
            backgroundColor: "var(--color-accent)",
            color: "#ffffff",
            opacity: isSubmitting ? 0.7 : 1,
            cursor: isSubmitting ? "not-allowed" : "pointer",
          }}
          onMouseEnter={
            !isSubmitting
              ? (e) =>
                  (e.currentTarget.style.backgroundColor =
                    "var(--color-accent-muted)")
              : undefined
          }
          onMouseLeave={
            !isSubmitting
              ? (e) =>
                  (e.currentTarget.style.backgroundColor =
                    "var(--color-accent)")
              : undefined
          }
        >
          {isSubmitting && <Spinner />}
          {isSubmitting ? "Submitting..." : "Submit Answers"}
        </button>
      </div>
    </div>
  );
}
