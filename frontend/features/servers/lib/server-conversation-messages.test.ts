import test from "node:test";
import assert from "node:assert/strict";

import {
  getChannelEventContent,
  getChannelEventLabelKey,
  getMessageSessionId,
  isExecutionDrilldownMessage,
} from "./server-conversation-messages.ts";
import type { ServerConversationMessage } from "../model/types.ts";

function createMessage(
  overrides: Partial<ServerConversationMessage>,
): ServerConversationMessage {
  return {
    id: "message-1",
    channelId: "channel-1",
    authorUserId: null,
    authorUser: null,
    messageType: "system",
    content: {},
    textPreview: null,
    threadRootMessageId: null,
    replyCount: 0,
    reactions: [],
    createdAt: "2026-05-08T00:00:00.000Z",
    updatedAt: "2026-05-08T00:00:00.000Z",
    ...overrides,
  };
}

test("getMessageSessionId returns trimmed session ids from system messages", () => {
  const message = createMessage({
    content: { source: "agent_execution", session_id: "  session-123  " },
  });

  assert.equal(getMessageSessionId(message), "session-123");
});

test("isExecutionDrilldownMessage accepts agent execution and agent session projections", () => {
  const executionMessage = createMessage({
    content: { source: "agent_execution", session_id: "session-1" },
  });
  const sessionMessage = createMessage({
    content: { source: "agent_session", session_id: "session-2" },
  });

  assert.equal(isExecutionDrilldownMessage(executionMessage), true);
  assert.equal(isExecutionDrilldownMessage(sessionMessage), true);
});

test("isExecutionDrilldownMessage rejects messages without a session id", () => {
  const message = createMessage({
    content: { source: "agent_session" },
  });

  assert.equal(isExecutionDrilldownMessage(message), false);
});

test("getChannelEventContent reads structured event payloads", () => {
  const message = createMessage({
    messageType: "event",
    content: {
      event_type: "task.created",
      actor_type: "agent",
      actor_label: "Planner",
      actor_agent_identity_id: "agent-1",
      title: "Fix parser",
      task_id: "task-1",
    },
  });

  assert.deepEqual(getChannelEventContent(message), {
    eventType: "task.created",
    actorType: "agent",
    actorUserId: null,
    actorLabel: "Planner",
    actorAgentIdentityId: "agent-1",
    actorAgentHandle: null,
    actorSessionId: null,
    targetUserId: null,
    targetAgentIdentityId: null,
    targetAgentHandle: null,
    targetLabel: null,
    membershipId: null,
    joinReason: null,
    taskId: "task-1",
    title: "Fix parser",
    status: null,
    priority: null,
    fromStatus: null,
    toStatus: null,
    assignee: undefined,
  });
});

test("getChannelEventLabelKey falls back for unknown event types", () => {
  assert.equal(
    getChannelEventLabelKey("channel.member_joined"),
    "conversationView.events.channelMemberJoined",
  );
  assert.equal(
    getChannelEventLabelKey("custom.event"),
    "conversationView.events.unknown",
  );
});
