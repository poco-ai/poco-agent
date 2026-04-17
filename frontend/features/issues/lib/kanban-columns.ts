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

export interface KanbanIssueMove {
  issueId: string;
  status: WorkspaceIssueStatus;
  position: number;
}

function getTimestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function groupIssuesByStatus(
  issues: WorkspaceIssue[],
): Map<WorkspaceIssueStatus, WorkspaceIssue[]> {
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

  return grouped;
}

function normalizePosition(position: number, columnSize: number): number {
  return Math.max(0, Math.min(position, columnSize));
}

export function buildKanbanColumns(
  issues: WorkspaceIssue[],
): KanbanColumnData[] {
  const grouped = groupIssuesByStatus(issues);

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

export function moveKanbanIssue(
  issues: WorkspaceIssue[],
  move: KanbanIssueMove,
): WorkspaceIssue[] {
  const sourceIssue = issues.find((issue) => issue.issue_id === move.issueId);
  if (!sourceIssue) {
    return issues;
  }

  const grouped = groupIssuesByStatus(
    issues.map((issue) => ({ ...issue })),
  );
  const sourceColumn = grouped.get(sourceIssue.status);
  const targetColumn = grouped.get(move.status);
  if (!sourceColumn || !targetColumn) {
    return issues;
  }

  const sourceIndex = sourceColumn.findIndex(
    (issue) => issue.issue_id === move.issueId,
  );
  if (sourceIndex === -1) {
    return issues;
  }

  const [movedIssue] = sourceColumn.splice(sourceIndex, 1);
  const targetIndex = normalizePosition(move.position, targetColumn.length);

  if (sourceIssue.status === move.status && sourceIndex === targetIndex) {
    return issues;
  }

  movedIssue.status = move.status;
  targetColumn.splice(targetIndex, 0, movedIssue);

  return KANBAN_COLUMN_ORDER.flatMap((status) =>
    (grouped.get(status) ?? []).map((issue, index) => ({
      ...issue,
      status,
      position: index,
    })),
  );
}

export function mergeMovedIssue(
  issues: WorkspaceIssue[],
  updatedIssue: WorkspaceIssue,
): WorkspaceIssue[] {
  const nextIssues = issues.map((issue) =>
    issue.issue_id === updatedIssue.issue_id ? updatedIssue : issue,
  );

  return moveKanbanIssue(nextIssues, {
    issueId: updatedIssue.issue_id,
    status: updatedIssue.status,
    position: updatedIssue.position,
  });
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
