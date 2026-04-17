import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceIssue } from "../model/types.ts";
import {
  KANBAN_COLUMN_ORDER,
  buildKanbanColumns,
  getNextMobileKanbanStatus,
  mergeMovedIssue,
  moveKanbanIssue,
} from "./kanban-columns.ts";

function createIssue(overrides: Partial<WorkspaceIssue> = {}): WorkspaceIssue {
  return {
    issue_id: "issue-1",
    workspace_id: "workspace-1",
    board_id: "board-1",
    title: "Fix login flicker",
    description: "Investigate the loading state after auth redirect",
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

test("buildKanbanColumns keeps the default status order and sorts issues by position", () => {
  const columns = buildKanbanColumns([
    createIssue({ issue_id: "issue-1", status: "done", position: 1 }),
    createIssue({ issue_id: "issue-2", status: "todo", position: 2 }),
    createIssue({ issue_id: "issue-3", status: "todo", position: 0 }),
    createIssue({ issue_id: "issue-4", status: "in_progress", position: 0 }),
  ]);

  assert.deepEqual(
    columns.map((column) => column.status),
    KANBAN_COLUMN_ORDER,
  );
  assert.deepEqual(
    columns.find((column) => column.status === "todo")?.issues.map(
      (issue) => issue.issue_id,
    ),
    ["issue-3", "issue-2"],
  );
});

test("buildKanbanColumns keeps empty columns so the board canvas remains stable", () => {
  const columns = buildKanbanColumns([
    createIssue({ issue_id: "issue-1", status: "done", position: 0 }),
  ]);

  assert.equal(columns.length, 4);
  assert.equal(
    columns.find((column) => column.status === "canceled")?.issues.length,
    0,
  );
});

test("getNextMobileKanbanStatus falls back to the first default column when selection is invalid", () => {
  assert.equal(getNextMobileKanbanStatus("blocked"), "todo");
  assert.equal(getNextMobileKanbanStatus("done"), "done");
});

test("moveKanbanIssue reorders issues within the same column", () => {
  const nextIssues = moveKanbanIssue(
    [
      createIssue({ issue_id: "issue-1", status: "todo", position: 0 }),
      createIssue({ issue_id: "issue-2", status: "todo", position: 1 }),
      createIssue({ issue_id: "issue-3", status: "todo", position: 2 }),
    ],
    {
      issueId: "issue-3",
      status: "todo",
      position: 0,
    },
  );

  assert.deepEqual(
    buildKanbanColumns(nextIssues)
      .find((column) => column.status === "todo")
      ?.issues.map((issue) => `${issue.issue_id}:${issue.position}`),
    ["issue-3:0", "issue-1:1", "issue-2:2"],
  );
});

test("moveKanbanIssue moves issues across columns and resequences both sides", () => {
  const nextIssues = moveKanbanIssue(
    [
      createIssue({ issue_id: "issue-1", status: "todo", position: 0 }),
      createIssue({ issue_id: "issue-2", status: "todo", position: 1 }),
      createIssue({ issue_id: "issue-3", status: "done", position: 0 }),
    ],
    {
      issueId: "issue-2",
      status: "done",
      position: 0,
    },
  );

  assert.deepEqual(
    buildKanbanColumns(nextIssues)
      .find((column) => column.status === "todo")
      ?.issues.map((issue) => `${issue.issue_id}:${issue.position}`),
    ["issue-1:0"],
  );
  assert.deepEqual(
    buildKanbanColumns(nextIssues)
      .find((column) => column.status === "done")
      ?.issues.map((issue) => `${issue.issue_id}:${issue.position}`),
    ["issue-2:0", "issue-3:1"],
  );
});

test("mergeMovedIssue keeps the optimistic order while refreshing the moved issue payload", () => {
  const optimisticIssues = moveKanbanIssue(
    [
      createIssue({ issue_id: "issue-1", status: "todo", position: 0 }),
      createIssue({ issue_id: "issue-2", status: "todo", position: 1 }),
      createIssue({ issue_id: "issue-3", status: "done", position: 0 }),
    ],
    {
      issueId: "issue-2",
      status: "done",
      position: 0,
    },
  );

  const nextIssues = mergeMovedIssue(
    optimisticIssues,
    createIssue({
      issue_id: "issue-2",
      status: "done",
      position: 0,
      updated_at: "2026-04-16T10:30:00Z",
      title: "Updated from server",
    }),
  );

  const movedIssue = nextIssues.find((issue) => issue.issue_id === "issue-2");
  assert.equal(movedIssue?.title, "Updated from server");
  assert.equal(movedIssue?.status, "done");
  assert.equal(movedIssue?.position, 0);
});
