// API client for backend communication

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  children: FileNode[] | null;
  extension: string | null;
}

export interface ScanResponse {
  project_name: string;
  root_path: string;
  file_tree: FileNode[];
  total_files: number;
  supported_files: number;
}

/**
 * Scan a project directory for supported files.
 * POST /api/projects/scan with project_name and path.
 */
export async function scanProject(
  projectName: string,
  path: string
): Promise<ScanResponse> {
  const response = await fetch("/api/projects/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_name: projectName, path }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    const message =
      errorData?.detail || `Scan failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json();
}
