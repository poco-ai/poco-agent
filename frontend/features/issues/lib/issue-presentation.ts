import type { TFunction } from "i18next";

import type { AgentAssignment, WorkspaceIssue } from "../model/types.ts";

function humanizeEnumToken(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function formatIssueStatus(
  t: TFunction,
  status: WorkspaceIssue["status"],
): string {
  return t(`issues.statuses.${status}`, humanizeEnumToken(status));
}

export function formatIssuePriority(
  t: TFunction,
  priority: WorkspaceIssue["priority"],
): string {
  return t(`issues.priorities.${priority}`, humanizeEnumToken(priority));
}

export function formatAssignmentStatus(
  t: TFunction,
  status: AgentAssignment["status"],
): string {
  return t(`issues.assignmentStatuses.${status}`, humanizeEnumToken(status));
}
