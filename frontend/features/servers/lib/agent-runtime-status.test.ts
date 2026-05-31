import test from "node:test";
import assert from "node:assert/strict";

import { getAgentRuntimeStatus } from "./agent-runtime-status.ts";
import type { ServerAgentItem } from "../model/types.ts";

function createAgent(
  overrides: Partial<ServerAgentItem> = {},
): ServerAgentItem {
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
    runtimeSummary: {
      id: "runtime-1",
      runtimeKey: "server_agent:agent-1",
      ownerType: "server_agent",
      ownerId: "agent-1",
      agentIdentityId: "agent-1",
      assignmentId: null,
      sessionId: null,
      containerId: null,
      lifecycleState: "sleeping",
      autoResume: true,
      idleTimeoutSeconds: 900,
      warmRetentionSeconds: 120,
      keepaliveUntil: null,
      lastActivityAt: "2026-05-17T00:00:00.000Z",
      lastStartedAt: null,
      lastStoppedAt: null,
      lastStopReason: null,
      workerId: null,
      browserEnabled: false,
      filesystemFingerprint: null,
    },
    createdAt: "2026-05-17T00:00:00.000Z",
    updatedAt: "2026-05-17T00:00:00.000Z",
    ...overrides,
  };
}

test("maps sleeping runtime to the shared sleeping presentation", () => {
  const status = getAgentRuntimeStatus(createAgent());

  assert.equal(status.state, "sleeping");
  assert.equal(status.labelKey, "runtime.states.sleeping");
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
      runtimeSummary: {
        ...createAgent().runtimeSummary!,
        lifecycleState: "running",
        sessionId: "session-1",
      },
    }),
  );

  assert.equal(status.state, "running");
  assert.equal(status.labelKey, "runtime.states.running");
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
  assert.equal(status.labelKey, "runtime.states.removed");
});
