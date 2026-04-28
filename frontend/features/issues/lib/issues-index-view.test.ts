import test from "node:test";
import assert from "node:assert/strict";

import type { WorkspaceBoard, WorkspaceIssue } from "../model/types.ts";
import {
  BOARD_PRIORITY_ORDER,
  buildBoardLanes,
  getIssuePriorityBucket,
} from "./issues-index-view.ts";

function createBoard(overrides: Partial<WorkspaceBoard> = {}): WorkspaceBoard {
  return {
    board_id: "board-1",
    workspace_id: "workspace-1",
    name: "Product polish",
    description: null,
    created_by: "user-1",
    updated_by: null,
    created_at: "2026-04-16T09:00:00Z",
    updated_at: "2026-04-16T09:00:00Z",
    ...overrides,
  };
}

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

test("getIssuePriorityBucket treats medium issues as the default unprioritized bucket", () => {
  assert.equal(getIssuePriorityBucket("medium"), "medium");
  assert.equal(getIssuePriorityBucket("high"), "high");
  assert.equal(getIssuePriorityBucket("urgent"), "high");
  assert.equal(getIssuePriorityBucket("low"), "low");
});

test("buildBoardLanes keeps board order and groups pending issues by priority bucket", () => {
  const lanes = buildBoardLanes(
    [
      createBoard({ board_id: "board-1", name: "Design debt" }),
      createBoard({ board_id: "board-2", name: "Runtime hardening" }),
    ],
    [
      createIssue({
        issue_id: "issue-1",
        board_id: "board-2",
        priority: "high",
        position: 1,
      }),
      createIssue({
        issue_id: "issue-2",
        board_id: "board-1",
        priority: "medium",
        position: 0,
      }),
      createIssue({
        issue_id: "issue-3",
        board_id: "board-1",
        priority: "urgent",
        position: 1,
      }),
      createIssue({
        issue_id: "issue-4",
        board_id: "board-1",
        priority: "high",
        position: 2,
      }),
    ],
  );

  assert.deepEqual(
    lanes.map((lane) => lane.board.board_id),
    ["board-1", "board-2"],
  );
  assert.deepEqual(BOARD_PRIORITY_ORDER, ["high", "medium", "low"]);
  assert.deepEqual(
    lanes[0].pendingSections.map((section) => ({
      priority: section.priority,
      issues: section.issues.map((issue) => issue.issue_id),
    })),
    [
      { priority: "high", issues: ["issue-3", "issue-4"] },
      { priority: "medium", issues: ["issue-2"] },
    ],
  );
  assert.deepEqual(
    lanes[1].pendingSections.map((section) => ({
      priority: section.priority,
      issues: section.issues.map((issue) => issue.issue_id),
    })),
    [{ priority: "high", issues: ["issue-1"] }],
  );
});

test("buildBoardLanes collapses done and canceled issues into the completed bucket", () => {
  const lanes = buildBoardLanes(
    [createBoard()],
    [
      createIssue({ issue_id: "issue-1", status: "todo", position: 0 }),
      createIssue({ issue_id: "issue-2", status: "done", position: 0 }),
      createIssue({ issue_id: "issue-3", status: "canceled", position: 1 }),
      createIssue({ issue_id: "issue-4", status: "in_progress", position: 1 }),
    ],
  );

  assert.deepEqual(
    lanes[0].pendingSections.flatMap((section) =>
      section.issues.map((issue) => issue.issue_id),
    ),
    ["issue-1", "issue-4"],
  );
  assert.deepEqual(
    lanes[0].completedIssues.map((issue) => issue.issue_id),
    ["issue-2", "issue-3"],
  );
  assert.equal(lanes[0].pendingCount, 2);
  assert.equal(lanes[0].completedCount, 2);
});
