export type ChannelTaskStatus = "todo" | "in_progress" | "in_review" | "done";

export type ChannelTaskView = "list" | "board";

export interface ChannelTaskActorSummary {
  actorType: "user" | "agent";
  userId?: string | null;
  agentIdentityId?: string | null;
  agentHandle?: string | null;
  label: string;
  avatarUrl?: string | null;
  visualKey?: string | null;
}

export interface ChannelTask {
  taskId: string;
  serverId: string;
  channelId: string;
  displayNumber: number;
  title: string;
  description?: string | null;
  status: ChannelTaskStatus;
  position: number;
  priority?: string | null;
  dueDate?: string | null;
  assigneeUserId?: string | null;
  assigneePresetId?: number | null;
  assigneeAgentIdentityId?: string | null;
  creator?: ChannelTaskActorSummary | null;
  assignee?: ChannelTaskActorSummary | null;
  reporterUserId?: string | null;
  relatedProjectId?: string | null;
  creatorUserId: string;
  updatedBy?: string | null;
  threadRootMessageId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ChannelTaskCreateInput {
  title: string;
  description?: string | null;
  priority?: "low" | "medium" | "high" | "urgent" | null;
  sourceMessageId?: string | null;
}

export interface ChannelTaskStatusUpdateInput {
  status: ChannelTaskStatus;
  position: number;
}

export interface ChannelTaskUpdateInput {
  title?: string;
  description?: string | null;
  priority?: "low" | "medium" | "high" | "urgent" | null;
  assigneeUserId?: string | null;
  assigneePresetId?: number | null;
  assigneeAgentIdentityId?: string | null;
}

export interface ChannelTaskActivityMessage {
  messageId: string;
  channelId: string;
  authorUserId?: string | null;
  messageType: "user" | "system" | "task" | "event";
  content: Record<string, unknown>;
  textPreview?: string | null;
  threadRootMessageId?: string | null;
  createdAt: string;
  updatedAt: string;
}
