import type { RunResponse } from "../../types/index.ts";
import { countFileChanges } from "../../lib/run-record-utils.ts";

export function hasRunArtifacts(run: RunResponse): boolean {
  const fileChangeCount = getRunFileChangeCount(run);
  return (
    fileChangeCount > 0 ||
    Boolean(
      run.workspace_manifest_key ||
      run.workspace_files_prefix ||
      run.workspace_archive_key ||
      run.workspace_export_status === "ready",
    )
  );
}

export function getRunFileChangeCount(run: RunResponse): number {
  const workspaceFileChangeCount =
    run.state_patch?.workspace_state?.file_change_count;
  if (typeof run.file_change_count === "number") {
    return run.file_change_count;
  }
  if (
    typeof workspaceFileChangeCount === "number" &&
    workspaceFileChangeCount > 0
  ) {
    return workspaceFileChangeCount;
  }
  return countFileChanges(run.state_patch?.workspace_state?.file_changes ?? []);
}

export function buildActionHint(
  run: RunResponse,
  hasToolExecutions: boolean,
): boolean {
  return hasRunArtifacts(run) || hasToolExecutions;
}

export function formatDurationSeconds(run: RunResponse): string | null {
  if (!run.started_at) return null;
  const startedAt = new Date(run.started_at).getTime();
  const endAt = run.finished_at
    ? new Date(run.finished_at).getTime()
    : Date.now();
  if (
    !Number.isFinite(startedAt) ||
    !Number.isFinite(endAt) ||
    endAt <= startedAt
  ) {
    return null;
  }
  const seconds = Math.max(1, Math.round((endAt - startedAt) / 1000));
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  return `${seconds}s`;
}

export function getStatusTone(status: string): {
  node: string;
  line: string;
  badge: string;
} {
  switch (status) {
    case "completed":
      return {
        node: "border-emerald-500/80 bg-emerald-500 text-white dark:border-emerald-400/80 dark:bg-emerald-400 dark:text-emerald-950",
        line: "bg-emerald-400/80 dark:bg-emerald-300/80",
        badge: "text-emerald-700 dark:text-emerald-300",
      };
    case "running":
    case "pending":
    case "claimed":
    case "queued":
    case "canceling":
      return {
        node: "border-primary/80 bg-primary text-primary-foreground dark:border-primary/70 dark:bg-primary dark:text-primary-foreground",
        line: "bg-primary/70 dark:bg-primary/80",
        badge: "text-primary dark:text-primary/90",
      };
    case "failed":
      return {
        node: "border-destructive/80 bg-destructive text-destructive-foreground dark:border-red-400/80 dark:bg-red-400 dark:text-red-950",
        line: "bg-destructive/70 dark:bg-red-400/80",
        badge: "text-destructive dark:text-red-300",
      };
    default:
      return {
        node: "border-border bg-muted/80 text-muted-foreground dark:border-border/80 dark:bg-muted/60 dark:text-muted-foreground",
        line: "bg-border dark:bg-border/80",
        badge: "text-muted-foreground dark:text-muted-foreground",
      };
  }
}
