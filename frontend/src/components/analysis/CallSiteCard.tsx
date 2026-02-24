"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import PromptDisplay from "./PromptDisplay";
import type { PromptInfo } from "./PromptDisplay";

export interface CallSiteInfo {
  file_path: string;
  framework: string;
  method: string;
  start_line: number;
  end_line: number;
  source: string;
  is_test: boolean;
  prompts: PromptInfo[];
}

interface CallSiteCardProps {
  site: CallSiteInfo;
}

function getLanguage(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase();
  if (ext === "py") return "python";
  if (ext === "ts" || ext === "tsx") return "typescript";
  if (ext === "js" || ext === "jsx") return "javascript";
  return "text";
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{
        transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
        transition: "transform 0.15s ease",
        flexShrink: 0,
      }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export default function CallSiteCard({ site }: CallSiteCardProps) {
  const [expanded, setExpanded] = useState(false);
  const language = getLanguage(site.file_path);

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        backgroundColor: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        marginBottom: "6px",
      }}
    >
      {/* Collapsed header row */}
      <div
        className="flex items-center gap-3 px-3 py-2.5 cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
        style={{
          borderBottom: expanded ? "1px solid var(--color-border)" : "none",
        }}
      >
        {/* File path */}
        <span
          className="text-xs font-mono flex-1 truncate"
          style={{ color: "var(--color-text)" }}
        >
          {site.file_path}
        </span>

        {/* Badges */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className="text-xs px-2 py-0.5 rounded-full font-medium"
            style={{
              backgroundColor: "var(--color-accent)",
              color: "#ffffff",
            }}
          >
            {site.framework}
          </span>
          {site.is_test && (
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{
                backgroundColor: "rgba(107, 114, 128, 0.2)",
                color: "var(--color-text-muted)",
              }}
            >
              test
            </span>
          )}
          <span
            className="text-xs font-mono"
            style={{ color: "var(--color-text-muted)" }}
          >
            L{site.start_line}
            {site.end_line !== site.start_line ? `-L${site.end_line}` : ""}
          </span>
        </div>

        {/* Chevron */}
        <span style={{ color: "var(--color-text-muted)" }}>
          <ChevronIcon expanded={expanded} />
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 pb-3">
          {/* Syntax-highlighted source */}
          <div className="rounded-md overflow-hidden mt-3" style={{ fontSize: "12px" }}>
            <SyntaxHighlighter
              language={language}
              style={oneDark}
              showLineNumbers
              startingLineNumber={site.start_line}
              customStyle={{
                margin: 0,
                borderRadius: "6px",
                fontSize: "12px",
              }}
            >
              {site.source}
            </SyntaxHighlighter>
          </div>

          {/* Prompts */}
          {site.prompts.length > 0 && <PromptDisplay prompts={site.prompts} />}
        </div>
      )}
    </div>
  );
}
