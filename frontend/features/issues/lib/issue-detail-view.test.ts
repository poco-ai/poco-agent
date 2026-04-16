import test from "node:test";
import assert from "node:assert/strict";

import type { AgentAssignment } from "../model/types.ts";
import { getAssignmentExecutionMeta } from "./issue-detail-view.ts";

function createAssignment(
  overrides: Partial<AgentAssignment> = {},
): AgentAssignment {
  return {
    assignment_id: "assignment-1",
    workspace_id: "workspace-1",
    issue_id: "issue-1",
    preset_id: 7,
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
    ...overrides,
  };
}

test("getAssignmentExecutionMeta returns safe defaults for missing assignments", () => {
  assert.deepEqual(getAssignmentExecutionMeta(null), {
    isScheduled: false,
    hasSession: false,
    hasRetainedContainer: false,
    lastTriggeredAt: null,
    lastCompletedAt: null,
  });
});

test("getAssignmentExecutionMeta reflects scheduled assignments and retained containers", () => {
  assert.deepEqual(
    getAssignmentExecutionMeta(
      createAssignment({
        trigger_mode: "scheduled_task",
        session_id: "session-1",
        container_id: "container-1",
        last_triggered_at: "2026-04-16T10:00:00Z",
        last_completed_at: "2026-04-16T10:05:00Z",
      }),
    ),
    {
      isScheduled: true,
      hasSession: true,
      hasRetainedContainer: true,
      lastTriggeredAt: "2026-04-16T10:00:00Z",
      lastCompletedAt: "2026-04-16T10:05:00Z",
    },
  );
});
