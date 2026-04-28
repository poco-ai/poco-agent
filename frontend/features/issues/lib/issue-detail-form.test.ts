import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceIssue } from "../model/types.ts";
import {
  createIssueDetailFormData,
  shouldScheduleIssueDetailAutoSave,
} from "./issue-detail-form.ts";

function createIssue(overrides: Partial<WorkspaceIssue> = {}): WorkspaceIssue {
  return {
    issue_id: "issue-1",
    workspace_id: "workspace-1",
    board_id: "board-1",
    title: "Fix issue detail autosave",
    description: "Keep server values stable when opening the dialog",
    status: "todo",
    position: 0,
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

test("createIssueDetailFormData preserves urgent priority from the backend", () => {
  const form = createIssueDetailFormData(
    createIssue({
      priority: "urgent",
      agent_assignment: {
        assignment_id: "assignment-1",
        workspace_id: "workspace-1",
        issue_id: "issue-1",
        preset_id: 1,
        trigger_mode: "scheduled_task",
        session_id: null,
        container_id: null,
        status: "pending",
        prompt: "Run the issue flow",
        schedule_cron: "0 * * * *",
        last_triggered_at: null,
        last_completed_at: null,
        created_by: "user-1",
        created_at: "2026-04-16T09:00:00Z",
        updated_at: "2026-04-16T09:00:00Z",
      },
    }),
  );

  assert.equal(form.priority, "urgent");
  assert.equal(form.triggerMode, "scheduled_task");
  assert.equal(form.scheduleCron, "0 * * * *");
});

test("shouldScheduleIssueDetailAutoSave skips the first server-driven form sync", () => {
  assert.equal(shouldScheduleIssueDetailAutoSave("loading", false), false);
  assert.equal(shouldScheduleIssueDetailAutoSave("loaded", true), false);
  assert.equal(shouldScheduleIssueDetailAutoSave("loaded", false), true);
});
