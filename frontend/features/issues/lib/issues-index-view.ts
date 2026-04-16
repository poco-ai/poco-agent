import type { WorkspaceIssue } from "../model/types.ts";

export interface BoardIssueSummary {
  totalIssues: number;
  aiAssignedIssues: number;
  runningIssues: number;
}

export function filterIssuesByQuery(
  issues: WorkspaceIssue[],
  query: string,
): WorkspaceIssue[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return issues;
  }

  return issues.filter((issue) => {
    return (
      issue.title.toLowerCase().includes(normalizedQuery) ||
      (issue.description ?? "").toLowerCase().includes(normalizedQuery)
    );
  });
}

export function summarizeBoardIssues(
  issues: WorkspaceIssue[],
): BoardIssueSummary {
  return {
    totalIssues: issues.length,
    aiAssignedIssues: issues.filter((issue) => issue.assignee_preset_id !== null)
      .length,
    runningIssues: issues.filter(
      (issue) => issue.agent_assignment?.status === "running",
    ).length,
  };
}
