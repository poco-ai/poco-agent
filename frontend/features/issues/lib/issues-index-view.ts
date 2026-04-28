import type { WorkspaceBoard, WorkspaceIssue } from "../model/types.ts";

export type BoardPriorityBucket = "high" | "medium" | "low";

export interface BoardPrioritySection {
  priority: BoardPriorityBucket;
  issues: WorkspaceIssue[];
}

export interface BoardLaneData {
  board: WorkspaceBoard;
  pendingSections: BoardPrioritySection[];
  completedIssues: WorkspaceIssue[];
  pendingCount: number;
  completedCount: number;
}

export const BOARD_PRIORITY_ORDER: BoardPriorityBucket[] = [
  "high",
  "medium",
  "low",
];

function getTimestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function sortIssues(left: WorkspaceIssue, right: WorkspaceIssue): number {
  if (left.position !== right.position) {
    return left.position - right.position;
  }
  return getTimestamp(right.updated_at) - getTimestamp(left.updated_at);
}

function isCompletedIssue(issue: WorkspaceIssue): boolean {
  return issue.status === "done" || issue.status === "canceled";
}

export function getIssuePriorityBucket(
  priority: WorkspaceIssue["priority"],
): BoardPriorityBucket {
  if (priority === "high") {
    return "high";
  }
  if (priority === "urgent") {
    return "high";
  }
  if (priority === "low") {
    return "low";
  }
  return "medium";
}

export function buildBoardLanes(
  boards: WorkspaceBoard[],
  issues: WorkspaceIssue[],
): BoardLaneData[] {
  return boards.map((board) => {
    const boardIssues = issues
      .filter((issue) => issue.board_id === board.board_id)
      .sort(sortIssues);
    const pendingIssues = boardIssues.filter((issue) => !isCompletedIssue(issue));
    const completedIssues = boardIssues.filter(isCompletedIssue);

    const pendingSections = BOARD_PRIORITY_ORDER.map((priority) => ({
      priority,
      issues: pendingIssues.filter(
        (issue) => getIssuePriorityBucket(issue.priority) === priority,
      ),
    })).filter((section) => section.issues.length > 0);

    return {
      board,
      pendingSections,
      completedIssues,
      pendingCount: pendingIssues.length,
      completedCount: completedIssues.length,
    };
  });
}

export function summarizeBoardIssues(issues: WorkspaceIssue[]): {
  totalIssues: number;
} {
  return {
    totalIssues: issues.length,
  };
}
