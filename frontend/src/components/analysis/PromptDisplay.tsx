"use client";

import { useState } from "react";

export interface PromptInfo {
  role: string;
  content: string;
  is_dynamic: boolean;
}

interface PromptDisplayProps {
  prompts: PromptInfo[];
}

const ROLE_COLORS: Record<string, { bg: string; color: string }> = {
  system: { bg: "rgba(59, 130, 246, 0.15)", color: "#3b82f6" },
  user: { bg: "rgba(34, 197, 94, 0.15)", color: "#22c55e" },
  assistant: { bg: "rgba(168, 85, 247, 0.15)", color: "#a855f7" },
  few_shot: { bg: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" },
  unknown: { bg: "rgba(107, 114, 128, 0.15)", color: "#6b7280" },
};

function getRoleStyle(role: string) {
  return ROLE_COLORS[role] ?? ROLE_COLORS.unknown;
}

const MAX_CONTENT_LENGTH = 200;

function PromptItem({ prompt }: { prompt: PromptInfo }) {
  const [expanded, setExpanded] = useState(false);
  const roleStyle = getRoleStyle(prompt.role);
  const isTruncated = prompt.content.length > MAX_CONTENT_LENGTH;
  const displayContent =
    isTruncated && !expanded
      ? prompt.content.slice(0, MAX_CONTENT_LENGTH) + "..."
      : prompt.content;

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        border: prompt.is_dynamic
          ? "1px dashed var(--color-border)"
          : "1px solid var(--color-border)",
        marginBottom: "8px",
      }}
    >
      {/* Role header */}
      <div
        className="flex items-center gap-2 px-3 py-1.5"
        style={{ backgroundColor: "var(--color-surface)" }}
      >
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full"
          style={{
            backgroundColor: roleStyle.bg,
            color: roleStyle.color,
          }}
        >
          {prompt.role}
        </span>
        {prompt.is_dynamic && (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: "rgba(107, 114, 128, 0.15)",
              color: "var(--color-text-muted)",
            }}
          >
            dynamic
          </span>
        )}
      </div>

      {/* Content */}
      <div
        className="px-3 py-2 text-xs font-mono whitespace-pre-wrap break-words"
        style={{
          backgroundColor: "var(--color-bg)",
          color: "var(--color-text)",
          lineHeight: "1.5",
        }}
      >
        {displayContent}
      </div>

      {/* Show more toggle */}
      {isTruncated && (
        <div
          className="px-3 py-1.5 text-xs cursor-pointer"
          style={{
            backgroundColor: "var(--color-surface)",
            color: "var(--color-accent)",
            borderTop: "1px solid var(--color-border)",
          }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show less" : "Show more"}
        </div>
      )}
    </div>
  );
}

export default function PromptDisplay({ prompts }: PromptDisplayProps) {
  if (prompts.length === 0) return null;

  return (
    <div className="mt-3">
      <div
        className="text-xs font-medium uppercase tracking-wider mb-2"
        style={{ color: "var(--color-text-muted)" }}
      >
        Extracted Prompts ({prompts.length})
      </div>
      {prompts.map((prompt, index) => (
        <PromptItem key={index} prompt={prompt} />
      ))}
    </div>
  );
}
