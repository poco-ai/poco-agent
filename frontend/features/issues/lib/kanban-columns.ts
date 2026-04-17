import type {
  WorkspaceIssue,
  WorkspaceIssueStatus,
} from "../model/types.ts";

export const KANBAN_COLUMN_ORDER: WorkspaceIssueStatus[] = [
  "todo",
  "in_progress",
  "done",
  "canceled",
];

export interface KanbanColumnData {
  status: WorkspaceIssueStatus;
  issues: WorkspaceIssue[];
}

function getTimestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

export function buildKanbanColumns(
  issues: WorkspaceIssue[],
): KanbanColumnData[] {
  const grouped = new Map<WorkspaceIssueStatus, WorkspaceIssue[]>(
    KANBAN_COLUMN_ORDER.map((status) => [status, []]),
  );

  for (const issue of issues) {
    const columnIssues = grouped.get(issue.status);
    if (!columnIssues) {
      continue;
    }
    columnIssues.push(issue);
  }

  return KANBAN_COLUMN_ORDER.map((status) => ({
    status,
    issues: (grouped.get(status) ?? []).sort((left, right) => {
      if (left.position !== right.position) {
        return left.position - right.position;
      }
      return getTimestamp(right.updated_at) - getTimestamp(left.updated_at);
    }),
  }));
}

export function getNextMobileKanbanStatus(
  currentStatus: string | null | undefined,
): WorkspaceIssueStatus {
  if (
    currentStatus &&
    KANBAN_COLUMN_ORDER.includes(currentStatus as WorkspaceIssueStatus)
  ) {
    return currentStatus as WorkspaceIssueStatus;
  }
  return KANBAN_COLUMN_ORDER[0];
}
