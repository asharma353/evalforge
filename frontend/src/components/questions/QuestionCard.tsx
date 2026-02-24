"use client";

import { useState } from "react";
import type { Question } from "@/lib/api";

interface QuestionCardProps {
  question: Question;
  value: string | string[];
  onChange: (questionId: string, value: string | string[]) => void;
  onSkip: (questionId: string) => void;
  isSkipped: boolean;
}

function formatCategory(category: string): string {
  return category
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export default function QuestionCard({
  question,
  value,
  onChange,
  onSkip,
  isSkipped,
}: QuestionCardProps) {
  const [skipHover, setSkipHover] = useState(false);

  const inputStyle = {
    backgroundColor: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    color: "var(--color-text)",
    opacity: isSkipped ? 0.4 : 1,
  };

  const renderInput = () => {
    const stringValue = typeof value === "string" ? value : "";
    const arrayValue = Array.isArray(value) ? value : [];

    switch (question.type) {
      case "text":
        return (
          <input
            type="text"
            value={stringValue}
            onChange={(e) => onChange(question.id, e.target.value)}
            placeholder={question.placeholder ?? ""}
            disabled={isSkipped}
            className="w-full px-3 py-2 rounded-md text-sm focus:outline-none"
            style={inputStyle}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-accent)")
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          />
        );

      case "textarea":
        return (
          <textarea
            value={stringValue}
            onChange={(e) => onChange(question.id, e.target.value)}
            placeholder={question.placeholder ?? ""}
            disabled={isSkipped}
            rows={4}
            className="w-full px-3 py-2 rounded-md text-sm focus:outline-none resize-y"
            style={inputStyle}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-accent)")
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          />
        );

      case "select":
        return (
          <select
            value={stringValue}
            onChange={(e) => onChange(question.id, e.target.value)}
            disabled={isSkipped}
            className="w-full px-3 py-2 rounded-md text-sm focus:outline-none"
            style={inputStyle}
          >
            <option value="">Select an option...</option>
            {question.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case "multi_select":
        return (
          <div className="flex flex-col gap-2">
            {question.options?.map((opt) => {
              const checked = arrayValue.includes(opt.value);
              return (
                <label
                  key={opt.value}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                  style={{
                    color: "var(--color-text)",
                    opacity: isSkipped ? 0.4 : 1,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    disabled={isSkipped}
                    onChange={() => {
                      const next = checked
                        ? arrayValue.filter((v) => v !== opt.value)
                        : [...arrayValue, opt.value];
                      onChange(question.id, next);
                    }}
                    className="rounded"
                    style={{ accentColor: "var(--color-accent)" }}
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        );

      default:
        return (
          <input
            type="text"
            value={stringValue}
            onChange={(e) => onChange(question.id, e.target.value)}
            placeholder={question.placeholder ?? ""}
            disabled={isSkipped}
            className="w-full px-3 py-2 rounded-md text-sm focus:outline-none"
            style={inputStyle}
          />
        );
    }
  };

  return (
    <div
      className="rounded-lg p-4 mb-3"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        opacity: isSkipped ? 0.7 : 1,
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1">
          <span
            className="text-xs font-medium uppercase tracking-wider"
            style={{ color: "var(--color-accent)" }}
          >
            {formatCategory(question.category)}
          </span>
          <p
            className="text-sm font-medium mt-1"
            style={{ color: "var(--color-text)" }}
          >
            {question.text}
          </p>
          {question.context_hint && (
            <p
              className="text-xs mt-1"
              style={{ color: "var(--color-text-muted)" }}
            >
              {question.context_hint}
            </p>
          )}
        </div>
        <button
          onClick={() => onSkip(question.id)}
          className="text-xs px-2 py-1 rounded transition-colors shrink-0"
          style={{
            backgroundColor: isSkipped
              ? "rgba(34, 197, 94, 0.1)"
              : "transparent",
            color: skipHover
              ? "var(--color-text)"
              : "var(--color-text-muted)",
            border: isSkipped
              ? "1px solid rgba(34, 197, 94, 0.3)"
              : "1px solid var(--color-border)",
          }}
          onMouseEnter={() => setSkipHover(true)}
          onMouseLeave={() => setSkipHover(false)}
        >
          {isSkipped ? "Unskip" : "Skip"}
        </button>
      </div>

      {isSkipped ? (
        <p
          className="text-xs italic"
          style={{ color: "var(--color-text-muted)" }}
        >
          Skipped &mdash; using default
        </p>
      ) : (
        <div className="mt-2">{renderInput()}</div>
      )}
    </div>
  );
}
