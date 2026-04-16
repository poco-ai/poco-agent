import assert from "node:assert/strict";
import test from "node:test";

import {
  formatAssignmentStatus,
  formatIssuePriority,
  formatIssueStatus,
} from "./issue-presentation.ts";

const translations: Record<string, string> = {
  "issues.assignmentStatuses.pending": "Pending",
  "issues.priorities.urgent": "Urgent",
  "issues.statuses.in_progress": "In progress",
};

function t(key: string, fallback?: string): string {
  return translations[key] ?? fallback ?? key;
}

test("formatIssueStatus resolves translated labels", () => {
  assert.equal(formatIssueStatus(t as never, "in_progress"), "In progress");
});

test("formatIssuePriority falls back to a humanized enum label", () => {
  assert.equal(formatIssuePriority(t as never, "high"), "High");
});

test("formatAssignmentStatus resolves translated labels", () => {
  assert.equal(formatAssignmentStatus(t as never, "pending"), "Pending");
});

test("formatIssuePriority keeps translated urgent label", () => {
  assert.equal(formatIssuePriority(t as never, "urgent"), "Urgent");
});
