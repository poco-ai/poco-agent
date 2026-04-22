import type { FileChange, ToolExecutionResponse } from "../types/index.ts";
import { getReplayFrameKind } from "../components/execution/computer-panel/replay/replay-utils.ts";

const FILE_CHANGE_STATUS_PRIORITY: Record<string, number> = {
  renamed: 4,
  deleted: 3,
  modified: 2,
  staged: 2,
  added: 1,
};

function normalizePath(path: string | null | undefined): string {
  return (path || "").replace(/\\/g, "/").trim();
}

export function normalizeFileChangeStatus(
  status: string | null | undefined,
): "added" | "modified" | "deleted" | "renamed" {
  const normalized = (status || "").trim().toLowerCase();
  if (normalized === "renamed") return "renamed";
  if (normalized === "deleted") return "deleted";
  if (normalized === "added") return "added";
  return "modified";
}

function mergeDiff(
  left: string | null | undefined,
  right: string | null | undefined,
): string | null {
  const a = left?.trim() ?? "";
  const b = right?.trim() ?? "";
  if (!a && !b) return null;
  if (!a) return b;
  if (!b || a === b) return a;
  return `${a}\n${b}`;
}

function pickMergedStatus(
  left: string | null | undefined,
  right: string | null | undefined,
): "added" | "modified" | "deleted" | "renamed" {
  const leftStatus = normalizeFileChangeStatus(left);
  const rightStatus = normalizeFileChangeStatus(right);
  return (FILE_CHANGE_STATUS_PRIORITY[rightStatus] ?? 0) >
    (FILE_CHANGE_STATUS_PRIORITY[leftStatus] ?? 0)
    ? rightStatus
    : leftStatus;
}

export function dedupeFileChanges(
  fileChanges: FileChange[] = [],
): FileChange[] {
  const merged = new Map<string, FileChange>();

  for (const change of fileChanges) {
    const path = normalizePath(change.path);
    if (!path) continue;

    const normalizedChange: FileChange = {
      ...change,
      path,
      status: normalizeFileChangeStatus(change.status),
      old_path: normalizePath(change.old_path) || null,
      diff: change.diff ?? null,
      added_lines: change.added_lines ?? 0,
      deleted_lines: change.deleted_lines ?? 0,
    };

    const existing = merged.get(path);
    if (!existing) {
      merged.set(path, normalizedChange);
      continue;
    }

    merged.set(path, {
      ...existing,
      status: pickMergedStatus(existing.status, normalizedChange.status),
      old_path: existing.old_path || normalizedChange.old_path,
      diff: mergeDiff(existing.diff, normalizedChange.diff),
      added_lines:
        (existing.added_lines ?? 0) + (normalizedChange.added_lines ?? 0),
      deleted_lines:
        (existing.deleted_lines ?? 0) + (normalizedChange.deleted_lines ?? 0),
    });
  }

  return Array.from(merged.values());
}

export function countFileChanges(fileChanges: FileChange[] = []): number {
  return dedupeFileChanges(fileChanges).length;
}

export function countReplaySteps(
  executions: ToolExecutionResponse[] = [],
): number {
  return executions.reduce((count, execution) => {
    return count + (getReplayFrameKind(execution) ? 1 : 0);
  }, 0);
}
