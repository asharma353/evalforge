"use client";

import { useState } from "react";
import { scanProject, type ScanResponse, type FileNode } from "@/lib/api";
import FileTreeView from "./FileTreeView";

interface UploadStepProps {
  onStepComplete: (stepId: string) => void;
  onStepData?: (stepId: string, data: unknown) => void;
}

/** Recursively extract all file paths (non-directory nodes) from a file tree. */
function extractFilePaths(tree: FileNode[]): string[] {
  const paths: string[] = [];
  for (const node of tree) {
    if (!node.is_dir) {
      paths.push(node.path);
    } else if (node.children) {
      paths.push(...extractFilePaths(node.children));
    }
  }
  return paths;
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
        d="M12 2C6.47715 2 2 6.47715 2 12"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        className="opacity-75"
      />
    </svg>
  );
}

export default function UploadStep({ onStepComplete, onStepData }: UploadStepProps) {
  const [projectName, setProjectName] = useState("");
  const [folderPath, setFolderPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResponse | null>(null);

  const canScan = projectName.trim() !== "" && folderPath.trim() !== "";

  const handleBrowse = async () => {
    // Use the File System Access API if available (Chromium browsers)
    if ("showDirectoryPicker" in window) {
      try {
        const dirHandle = await (
          window as unknown as {
            showDirectoryPicker: () => Promise<{ name: string }>;
          }
        ).showDirectoryPicker();
        // showDirectoryPicker only gives us the directory name, not the full path.
        // The full path is not accessible for security reasons.
        // We set the name as a hint; user will still need to provide the full path.
        setFolderPath(dirHandle.name);
      } catch {
        // User cancelled the picker
      }
    }
  };

  const handleScan = async () => {
    if (!canScan) return;

    setScanning(true);
    setError(null);

    try {
      const result = await scanProject(projectName.trim(), folderPath.trim());
      setScanResult(result);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred";
      setError(message);
    } finally {
      setScanning(false);
    }
  };

  const handleConfirm = () => {
    if (scanResult && onStepData) {
      const filePaths = extractFilePaths(scanResult.file_tree);
      onStepData("upload", {
        projectPath: scanResult.root_path,
        filePaths,
      });
    }
    onStepComplete("upload");
  };

  const handleChangePath = () => {
    setScanResult(null);
    setError(null);
  };

  // Phase 2: Show scan results
  if (scanResult) {
    return (
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="max-w-2xl mx-auto">
          <h2
            className="text-xl font-semibold mb-1"
            style={{ color: "var(--color-text)" }}
          >
            Project Setup
          </h2>
          <p
            className="text-sm mb-6"
            style={{ color: "var(--color-text-muted)" }}
          >
            Review the detected files for{" "}
            <span style={{ color: "var(--color-text)" }}>
              {scanResult.project_name}
            </span>
          </p>

          {/* Summary */}
          <div
            className="rounded-md px-4 py-3 mb-4 text-sm"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
            }}
          >
            <span style={{ color: "var(--color-accent)" }}>
              {scanResult.supported_files}
            </span>{" "}
            supported files found in{" "}
            <span style={{ color: "var(--color-text-muted)" }}>
              {scanResult.total_files}
            </span>{" "}
            total
          </div>

          {/* File tree */}
          <div
            className="rounded-md overflow-hidden mb-6"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
            }}
          >
            <div
              className="px-4 py-2 text-xs font-medium uppercase tracking-wider"
              style={{
                color: "var(--color-text-muted)",
                borderBottom: "1px solid var(--color-border)",
              }}
            >
              File Tree
            </div>
            <div className="px-2">
              <FileTreeView tree={scanResult.file_tree} />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleConfirm}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor: "var(--color-accent)",
                color: "#ffffff",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.backgroundColor =
                  "var(--color-accent-muted)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor =
                  "var(--color-accent)")
              }
            >
              Confirm & Continue
            </button>
            <button
              onClick={handleChangePath}
              className="px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer"
              style={{
                backgroundColor: "transparent",
                color: "var(--color-text-muted)",
                border: "1px solid var(--color-border)",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.backgroundColor = "var(--color-surface)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.backgroundColor = "transparent")
              }
            >
              Change Path
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Phase 1: Input form
  return (
    <div className="flex-1 p-8 flex items-center justify-center">
      <div className="w-full max-w-md">
        <h2
          className="text-xl font-semibold mb-1"
          style={{ color: "var(--color-text)" }}
        >
          Project Setup
        </h2>
        <p
          className="text-sm mb-6"
          style={{ color: "var(--color-text-muted)" }}
        >
          Enter your project name and provide the path to your codebase folder
          to get started.
        </p>

        {/* Project name */}
        <div className="mb-4">
          <label
            className="block text-xs font-medium mb-1.5 uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)" }}
          >
            Project Name
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="My LLM App"
            className="w-full rounded-md px-3 py-2 text-sm outline-none transition-colors"
            style={{
              backgroundColor: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text)",
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-accent)")
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = "var(--color-border)")
            }
          />
        </div>

        {/* Folder path */}
        <div className="mb-6">
          <label
            className="block text-xs font-medium mb-1.5 uppercase tracking-wider"
            style={{ color: "var(--color-text-muted)" }}
          >
            Codebase Path
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="/path/to/your/project"
              className="flex-1 rounded-md px-3 py-2 text-sm outline-none transition-colors"
              style={{
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text)",
              }}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--color-accent)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor = "var(--color-border)")
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" && canScan && !scanning) {
                  handleScan();
                }
              }}
            />
            {"showDirectoryPicker" in
              (typeof window !== "undefined" ? window : {}) && (
              <button
                onClick={handleBrowse}
                className="px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer shrink-0"
                style={{
                  backgroundColor: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-muted)",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.borderColor = "var(--color-accent)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.borderColor = "var(--color-border)")
                }
              >
                Browse
              </button>
            )}
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div
            className="rounded-md px-3 py-2 mb-4 text-sm"
            style={{
              backgroundColor: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#ef4444",
            }}
          >
            {error}
          </div>
        )}

        {/* Scan button */}
        <button
          onClick={handleScan}
          disabled={!canScan || scanning}
          className="w-full px-4 py-2.5 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2"
          style={{
            backgroundColor:
              canScan && !scanning
                ? "var(--color-accent)"
                : "var(--color-surface)",
            color:
              canScan && !scanning ? "#ffffff" : "var(--color-text-muted)",
            border:
              canScan && !scanning
                ? "none"
                : "1px solid var(--color-border)",
            cursor: canScan && !scanning ? "pointer" : "not-allowed",
            opacity: canScan && !scanning ? 1 : 0.6,
          }}
        >
          {scanning && <Spinner />}
          {scanning ? "Scanning..." : "Scan"}
        </button>
      </div>
    </div>
  );
}
