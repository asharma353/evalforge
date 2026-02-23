"use client";

import { useState } from "react";
import type { FileNode } from "@/lib/api";

interface FileTreeViewProps {
  tree: FileNode[];
}

interface TreeItemProps {
  node: FileNode;
  depth: number;
  defaultExpanded?: boolean;
}

/** Return a subtle color hint based on file extension. */
function extensionColor(ext: string | null): string {
  switch (ext) {
    case ".py":
      return "#3572A5"; // Python blue
    case ".ts":
    case ".tsx":
      return "#3178C6"; // TypeScript blue
    case ".js":
    case ".jsx":
      return "#F7DF1E"; // JavaScript yellow
    default:
      return "var(--color-text-muted)";
  }
}

function ChevronRight({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M6 4L10 8L6 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 6L8 10L12 6"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M2 4C2 3.44772 2.44772 3 3 3H6.17157C6.43679 3 6.69114 3.10536 6.87868 3.29289L7.70711 4.12132C7.89464 4.30886 8.149 4.41421 8.41421 4.41421H13C13.5523 4.41421 14 4.86193 14 5.41421V12C14 12.5523 13.5523 13 13 13H3C2.44772 13 2 12.5523 2 12V4Z"
        stroke="var(--color-accent)"
        strokeWidth="1.2"
        fill="none"
      />
    </svg>
  );
}

function FileIcon({ color }: { color: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 2H9.5L12 4.5V14H4V2Z"
        stroke={color}
        strokeWidth="1.2"
        fill="none"
      />
      <path d="M9.5 2V4.5H12" stroke={color} strokeWidth="1.2" fill="none" />
    </svg>
  );
}

function TreeItem({ node, depth, defaultExpanded = false }: TreeItemProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (node.is_dir) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 w-full text-left py-0.5 hover:bg-white/5 rounded transition-colors"
          style={{ paddingLeft: `${depth * 16}px` }}
        >
          <span
            className="shrink-0 transition-transform"
            style={{ color: "var(--color-text-muted)" }}
          >
            {expanded ? <ChevronDown /> : <ChevronRight />}
          </span>
          <span className="shrink-0">
            <FolderIcon />
          </span>
          <span
            className="text-sm font-mono truncate"
            style={{ color: "var(--color-text)" }}
          >
            {node.name}
          </span>
        </button>
        {expanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeItem key={child.path} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  const color = extensionColor(node.extension);

  return (
    <div
      className="flex items-center gap-1.5 py-0.5"
      style={{ paddingLeft: `${depth * 16 + 16}px` }}
    >
      <span className="shrink-0">
        <FileIcon color={color} />
      </span>
      <span
        className="text-sm font-mono truncate"
        style={{ color: "var(--color-text-muted)" }}
      >
        {node.name}
      </span>
    </div>
  );
}

export default function FileTreeView({ tree }: FileTreeViewProps) {
  if (tree.length === 0) {
    return (
      <div
        className="text-sm py-4 text-center"
        style={{ color: "var(--color-text-muted)" }}
      >
        No files found.
      </div>
    );
  }

  return (
    <div className="py-2 max-h-96 overflow-y-auto">
      {tree.map((node) => (
        <TreeItem
          key={node.path}
          node={node}
          depth={0}
          defaultExpanded={true}
        />
      ))}
    </div>
  );
}
