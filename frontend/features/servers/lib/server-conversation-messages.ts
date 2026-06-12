import type {
  ServerChannelEventContent,
  ServerConversationMessage,
} from "@/features/servers/model/types";

export function getMessageSessionId(
  message: ServerConversationMessage,
): string | null {
  if (message.messageType !== "system") {
    return null;
  }
  const rawSessionId = message.content.session_id;
  if (typeof rawSessionId !== "string") {
    return null;
  }
  const sessionId = rawSessionId.trim();
  return sessionId ? sessionId : null;
}

export function isExecutionDrilldownMessage(
  message: ServerConversationMessage,
): boolean {
  if (message.messageType !== "system") {
    return false;
  }
  const source =
    typeof message.content.source === "string"
      ? message.content.source.trim().toLowerCase()
      : "";
  if (source !== "agent_execution" && source !== "agent_session") {
    return false;
  }
  return getMessageSessionId(message) !== null;
}

function readString(
  content: Record<string, unknown>,
  key: string,
): string | null {
  const value = content[key];
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed || null;
}

function readNumberOrString(
  content: Record<string, unknown>,
  key: string,
): number | string | null {
  const value = content[key];
  if (typeof value === "number" || typeof value === "string") {
    return value;
  }
  return null;
}

export function getChannelEventContent(
  message: ServerConversationMessage,
): ServerChannelEventContent | null {
  if (message.messageType !== "event") {
    return null;
  }
  const eventType =
    readString(message.content, "event_type") ??
    readString(message.content, "event");
  if (!eventType) {
    return null;
  }
  return {
    eventType,
    actorType: readString(message.content, "actor_type"),
    actorUserId: readString(message.content, "actor_user_id"),
    actorLabel: readString(message.content, "actor_label"),
    actorAgentIdentityId: readString(
      message.content,
      "actor_agent_identity_id",
    ),
    actorAgentHandle: readString(message.content, "actor_agent_handle"),
    actorSessionId: readString(message.content, "actor_session_id"),
    targetUserId: readString(message.content, "target_user_id"),
    targetAgentIdentityId: readString(
      message.content,
      "target_agent_identity_id",
    ),
    targetAgentHandle: readString(message.content, "target_agent_handle"),
    targetLabel: readString(message.content, "target_label"),
    membershipId: readNumberOrString(message.content, "membership_id"),
    joinReason: readString(message.content, "join_reason"),
    taskId: readString(message.content, "task_id"),
    taskNumber: readNumberOrString(message.content, "task_number"),
    taskTitle: readString(message.content, "task_title"),
    title: readString(message.content, "title"),
    status: readString(message.content, "status"),
    priority: readString(message.content, "priority"),
    commentText: readString(message.content, "comment_text"),
    fromStatus: readString(message.content, "from_status"),
    toStatus: readString(message.content, "to_status"),
    artifactId: readString(message.content, "artifact_id"),
    artifactDisplayName: readString(message.content, "artifact_display_name"),
    artifactLogicalPath: readString(message.content, "artifact_logical_path"),
    artifactMimeType: readString(message.content, "artifact_mime_type"),
    artifactSizeBytes: readNumberOrString(
      message.content,
      "artifact_size_bytes",
    ),
    fromAssignee: message.content.from_assignee,
    toAssignee: message.content.to_assignee,
    assignee: message.content.assignee,
  };
}

export function getChannelEventLabelKey(eventType: string): string {
  switch (eventType) {
    case "channel.member_joined":
      return "conversationView.events.channelMemberJoined";
    case "channel.agent_joined":
      return "conversationView.events.channelAgentJoined";
    case "task.created":
      return "conversationView.events.taskCreated";
    case "task.status_changed":
      return "conversationView.events.taskStatusChanged";
    case "task.assigned":
      return "conversationView.events.taskAssigned";
    case "task.reassigned":
      return "conversationView.events.taskReassigned";
    case "task.unassigned":
      return "conversationView.events.taskUnassigned";
    case "task.updated":
      return "conversationView.events.taskUpdated";
    case "task.commented":
      return "conversationView.events.taskCommented";
    case "artifact.uploaded":
      return "conversationView.events.artifactUploaded";
    case "artifact.deleted":
      return "conversationView.events.artifactDeleted";
    case "conversation.shared":
      return "conversationView.events.conversationShared";
    default:
      return "conversationView.events.unknown";
  }
}
