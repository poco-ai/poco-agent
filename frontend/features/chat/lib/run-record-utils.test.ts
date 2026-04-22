import test from "node:test";
import assert from "node:assert/strict";

import {
  countFileChanges,
  countReplaySteps,
  dedupeFileChanges,
} from "./run-record-utils.ts";
import {
  getRunFileChangeCount,
  hasRunArtifacts,
} from "../components/layout/run-timeline-utils.ts";
import type { RunResponse, ToolExecutionResponse } from "../types/index.ts";

function buildToolExecution(toolName: string): ToolExecutionResponse {
  return {
    id: crypto.randomUUID(),
    run_id: crypto.randomUUID(),
    message_id: 1,
    tool_use_id: crypto.randomUUID(),
    tool_name: toolName,
    tool_input: {},
    tool_output: {},
    is_error: false,
    duration_ms: 10,
    created_at: "2026-04-22T00:00:00Z",
    updated_at: "2026-04-22T00:00:00Z",
  };
}

function buildRun(overrides: Partial<RunResponse> = {}): RunResponse {
  return {
    run_id: crypto.randomUUID(),
    session_id: crypto.randomUUID(),
    user_message_id: 1,
    status: "completed",
    permission_mode: "default",
    progress: 100,
    schedule_mode: "immediate",
    scheduled_at: "2026-04-22T00:00:00Z",
    claimed_by: null,
    lease_expires_at: null,
    attempts: 1,
    last_error: null,
    started_at: null,
    finished_at: null,
    created_at: "2026-04-22T00:00:00Z",
    updated_at: "2026-04-22T00:00:00Z",
    ...overrides,
  };
}

test("dedupeFileChanges merges duplicate paths and keeps stronger status", () => {
  const result = dedupeFileChanges([
    {
      path: "src/a.ts",
      status: "modified",
      added_lines: 1,
      deleted_lines: 0,
      diff: "left diff",
    },
    {
      path: "src/a.ts",
      status: "deleted",
      added_lines: 0,
      deleted_lines: 3,
      diff: "right diff",
    },
  ]);

  assert.equal(result.length, 1);
  assert.equal(result[0]?.status, "deleted");
  assert.equal(result[0]?.added_lines, 1);
  assert.equal(result[0]?.deleted_lines, 3);
  assert.equal(result[0]?.diff, "left diff\nright diff");
});

test("countFileChanges counts unique normalized paths only", () => {
  const count = countFileChanges([
    { path: "src\\a.ts", status: "modified" },
    { path: "src/a.ts", status: "modified" },
    { path: " src/b.ts ", status: "added" },
  ]);

  assert.equal(count, 2);
});

test("countReplaySteps counts only replayable tool executions", () => {
  const count = countReplaySteps([
    buildToolExecution("bash"),
    buildToolExecution("mcp____poco_playwright__browser_click"),
    buildToolExecution("Read"),
    buildToolExecution("unknown_tool"),
  ]);

  assert.equal(count, 3);
});

test("getRunFileChangeCount prefers run summary fields before fallback counting", () => {
  const explicitRunCount = buildRun({
    file_change_count: 6,
    state_patch: {
      workspace_state: {
        file_change_count: 2,
        file_changes: [{ path: "src/a.ts", status: "modified" }],
        last_change: "2026-04-22T00:00:00Z",
      },
    },
  });
  assert.equal(getRunFileChangeCount(explicitRunCount), 6);

  const workspaceCountRun = buildRun({
    state_patch: {
      workspace_state: {
        file_change_count: 4,
        file_changes: [{ path: "src/a.ts", status: "modified" }],
        last_change: "2026-04-22T00:00:00Z",
      },
    },
  });
  assert.equal(getRunFileChangeCount(workspaceCountRun), 4);

  const fallbackRun = buildRun({
    state_patch: {
      workspace_state: {
        file_changes: [
          { path: "src/a.ts", status: "modified" },
          { path: "src/a.ts", status: "modified" },
          { path: "src/b.ts", status: "added" },
        ],
        last_change: "2026-04-22T00:00:00Z",
      },
    },
  });
  assert.equal(getRunFileChangeCount(fallbackRun), 2);
});

test("hasRunArtifacts returns true for file changes or exported workspace metadata", () => {
  const withFiles = buildRun({
    file_change_count: 1,
  });
  assert.equal(hasRunArtifacts(withFiles), true);

  const withWorkspaceExport = buildRun({
    workspace_export_status: "ready",
  });
  assert.equal(hasRunArtifacts(withWorkspaceExport), true);

  const emptyRun = buildRun();
  assert.equal(hasRunArtifacts(emptyRun), false);
});
