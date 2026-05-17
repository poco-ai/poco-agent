import test from "node:test";
import assert from "node:assert/strict";

import { getAgentRuntimeStatus } from "./agent-runtime-status.ts";
import type { ServerAgentItem } from "../model/types.ts";

function createAgent(overrides: Partial<ServerAgentItem> = {}): ServerAgentItem {
  return {
    id: "agent-1",
    serverId: "server-1",
    presetId: 1,
    handle: "reviewer",
    displayName: "Reviewer",
    description: null,
    visualKey: "preset-visual-1",
    visibility: "server",
    lifecycleState: "active",
    createdBy: "user-1",
    updatedBy: "user-1",
    removedAt: null,
    removedBy: null,
    persistentState: {
      id: "state-1",
      stateRootPath: "agents/agent-1",
      profilePath: "agents/agent-1/profile.json",
      memoryPath: "agents/agent-1/MEMORY.md",
      notesDirPath: "agents/agent-1/notes",
      stateDirPath: "agents/agent-1/state",
      artifactsDirPath: "agents/agent-1/artifacts",
      stateVersion: 1,
      runtimeStatus: "idle",
      activeTaskId: null,
      activeSessionId: null,
      lastSyncedAt: "2026-05-17T00:00:00.000Z",
      lastWrittenAt: "2026-05-17T00:00:00.000Z",
    },
    createdAt: "2026-05-17T00:00:00.000Z",
    updatedAt: "2026-05-17T00:00:00.000Z",
    ...overrides,
  };
}

test("maps idle runtime to the shared idle presentation", () => {
  const status = getAgentRuntimeStatus(createAgent());

  assert.equal(status.state, "idle");
  assert.equal(status.labelKey, "conversationView.colleagues.runtimeStates.idle");
  assert.equal(status.rawRuntimeStatus, "idle");
  assert.equal(status.hasActiveExecution, false);
});

test("treats active session/task markers as active even when raw runtime says idle", () => {
  const status = getAgentRuntimeStatus(
    createAgent({
      persistentState: {
        ...createAgent().persistentState!,
        runtimeStatus: "idle",
        activeSessionId: "session-1",
      },
    }),
  );

  assert.equal(status.state, "active");
  assert.equal(
    status.labelKey,
    "conversationView.colleagues.runtimeStates.active",
  );
  assert.equal(status.hasActiveExecution, true);
});

test("prefers removed state over runtime markers", () => {
  const status = getAgentRuntimeStatus(
    createAgent({
      removedAt: "2026-05-17T00:00:00.000Z",
      persistentState: {
        ...createAgent().persistentState!,
        runtimeStatus: "busy",
        activeSessionId: "session-1",
      },
    }),
  );

  assert.equal(status.state, "removed");
  assert.equal(
    status.labelKey,
    "conversationView.colleagues.runtimeStates.removed",
  );
});
