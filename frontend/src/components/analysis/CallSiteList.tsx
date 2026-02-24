"use client";

import { useState } from "react";
import CallSiteCard from "./CallSiteCard";
import type { CallSiteInfo } from "./CallSiteCard";

interface CallSiteListProps {
  callSites: CallSiteInfo[];
}

function FileGroup({
  filePath,
  sites,
}: {
  filePath: string;
  sites: CallSiteInfo[];
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="mb-4">
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer select-none mb-1"
        onClick={() => setCollapsed(!collapsed)}
        style={{
          backgroundColor: "var(--color-surface)",
          border: "1px solid var(--color-border)",
        }}
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transform: collapsed ? "rotate(-90deg)" : "rotate(0deg)",
            transition: "transform 0.15s ease",
            color: "var(--color-text-muted)",
            flexShrink: 0,
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
        <span
          className="text-xs font-mono flex-1 truncate"
          style={{ color: "var(--color-text)" }}
        >
          {filePath}
        </span>
        <span
          className="text-xs px-2 py-0.5 rounded-full"
          style={{
            backgroundColor: "rgba(107, 114, 128, 0.15)",
            color: "var(--color-text-muted)",
          }}
        >
          {sites.length} {sites.length === 1 ? "call site" : "call sites"}
        </span>
      </div>

      {!collapsed && (
        <div className="pl-4">
          {sites.map((site, index) => (
            <CallSiteCard key={index} site={site} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CallSiteList({ callSites }: CallSiteListProps) {
  // Empty state
  if (callSites.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="mb-4"
          style={{ color: "var(--color-text-muted)" }}
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <p
          className="text-sm font-medium mb-1"
          style={{ color: "var(--color-text)" }}
        >
          No LLM call sites detected
        </p>
        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          No LLM API calls were found in this codebase. Make sure the project
          contains Python or JavaScript files using LLM frameworks.
        </p>
      </div>
    );
  }

  // Count unique files
  const uniqueFiles = new Set(callSites.map((s) => s.file_path));

  // Summary line
  const summary = (
    <div
      className="text-sm mb-4"
      style={{ color: "var(--color-text-muted)" }}
    >
      <span style={{ color: "var(--color-text)" }}>{callSites.length}</span>{" "}
      call {callSites.length === 1 ? "site" : "sites"} found across{" "}
      <span style={{ color: "var(--color-text)" }}>{uniqueFiles.size}</span>{" "}
      {uniqueFiles.size === 1 ? "file" : "files"}
    </div>
  );

  // Group by file when 10+ call sites
  if (callSites.length >= 10) {
    const grouped: Record<string, CallSiteInfo[]> = {};
    for (const site of callSites) {
      if (!grouped[site.file_path]) grouped[site.file_path] = [];
      grouped[site.file_path].push(site);
    }

    return (
      <div>
        {summary}
        {Object.entries(grouped).map(([filePath, sites]) => (
          <FileGroup key={filePath} filePath={filePath} sites={sites} />
        ))}
      </div>
    );
  }

  // Flat list for < 10 call sites
  return (
    <div>
      {summary}
      {callSites.map((site, index) => (
        <CallSiteCard key={index} site={site} />
      ))}
    </div>
  );
}
