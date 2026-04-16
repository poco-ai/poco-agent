import test from "node:test";
import assert from "node:assert/strict";

import type { WorkspaceIssue } from "../model/types.ts";
import {
  filterIssuesByQuery,
  summarizeBoardIssues,
} from "./issues-index-view.ts";

function createIssue(overrides: Partial<WorkspaceIssue> = {}): WorkspaceIssue {
  return {
    issue_id: "issue-1",
    workspace_id: "workspace-1",
    board_id: "board-1",
    title: "Fix login flicker",
    description: "Investigate the loading state after auth redirect",
    status: "todo",
    type: "task",
    priority: "medium",
    due_date: null,
    assignee_user_id: null,
    assignee_preset_id: null,
    reporter_user_id: null,
    related_project_id: null,
    creator_user_id: "user-1",
    updated_by: null,
    agent_assignment: null,
    created_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
    ...overrides,
  };
}

test("filterIssuesByQuery matches issue title and description", () => {
  const issues = [
    createIssue({ issue_id: "issue-1", title: "Fix login flicker" }),
    createIssue({
      issue_id: "issue-2",
      title: "Refine board shell",
      description: "Improve issue browsing density",
    }),
  ];

  assert.deepEqual(
    filterIssuesByQuery(issues, "shell").map((issue) => issue.issue_id),
    ["issue-2"],
  );
  assert.deepEqual(
    filterIssuesByQuery(issues, "login").map((issue) => issue.issue_id),
    ["issue-1"],
  );
});

test("summarizeBoardIssues reports totals, ai assignments, and running executions", () => {
  const issues = [
    createIssue({ issue_id: "issue-1" }),
    createIssue({
      issue_id: "issue-2",
      assignee_preset_id: 3,
      agent_assignment: {
        assignment_id: "assignment-2",
        workspace_id: "workspace-1",
        issue_id: "issue-2",
        preset_id: 3,
        trigger_mode: "persistent_sandbox",
        session_id: null,
        container_id: null,
        status: "pending",
        prompt: "Prompt",
        schedule_cron: null,
        last_triggered_at: null,
        last_completed_at: null,
        created_by: "user-1",
        created_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    }),
    createIssue({
      issue_id: "issue-3",
      assignee_preset_id: 4,
      agent_assignment: {
        assignment_id: "assignment-3",
        workspace_id: "workspace-1",
        issue_id: "issue-3",
        preset_id: 4,
        trigger_mode: "scheduled_task",
        session_id: null,
        container_id: null,
        status: "running",
        prompt: "Prompt",
        schedule_cron: "0 * * * *",
        last_triggered_at: null,
        last_completed_at: null,
        created_by: "user-1",
        created_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    }),
  ];

  assert.deepEqual(summarizeBoardIssues(issues), {
    totalIssues: 3,
    aiAssignedIssues: 2,
    runningIssues: 1,
  });
});
