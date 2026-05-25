export type ServerKind = "personal" | "shared";
export type ServerChannelVisibility = "public" | "private";
export type ServerConversationType = "channel" | "direct_message";
export type ServerSystemChannelType = "personal" | "public";
export type ServerRole = "owner" | "admin" | "member";

export interface ServerUserPublicProfile {
  userId: string;
  displayName?: string | null;
  avatarUrl?: string | null;
}

export interface ServerAgentPersistentState {
  id: string;
  stateRootPath: string;
  profilePath: string;
  memoryPath: string;
  notesDirPath: string;
  stateDirPath: string;
  artifactsDirPath: string;
  stateVersion: number;
  runtimeStatus: string;
  activeTaskId?: string | null;
  activeSessionId?: string | null;
  lastSyncedAt?: string | null;
  lastWrittenAt?: string | null;
}

export interface ServerAgentItem {
  id: string;
  serverId: string;
  presetId: number;
  handle: string;
  displayName: string;
  description?: string | null;
  visualKey: string;
  visibility: string;
  lifecycleState: string;
  createdBy: string;
  updatedBy?: string | null;
  removedAt?: string | null;
  removedBy?: string | null;
  persistentState?: ServerAgentPersistentState | null;
  createdAt: string;
  updatedAt: string;
}

export interface ServerItem {
  id: string;
  name: string;
  slug: string;
  kind: ServerKind;
  ownerUserId: string;
  createdAt: string;
  updatedAt: string;
}

export interface ServerMemberItem {
  id: number;
  serverId: string;
  userId: string;
  user?: ServerUserPublicProfile | null;
  role: ServerRole;
  joinedAt: string;
  invitedBy?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface ServerInviteItem {
  id: string;
  serverId: string;
  token: string;
  role: ServerRole;
  expiresAt: string;
  createdBy: string;
  maxUses: number;
  usedCount: number;
  revokedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ServerChannelItem {
  id: string;
  serverId: string;
  name: string;
  slug: string;
  description?: string | null;
  conversationType: ServerConversationType;
  visibility: ServerChannelVisibility;
  systemChannelType?: ServerSystemChannelType | null;
  isSystemChannel: boolean;
  directUserId?: string | null;
  directAgentIdentityId?: string | null;
  createdBy: string | null;
  archivedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ServerChannelMemberItem {
  id: number;
  channelId: string;
  userId: string;
  user?: ServerUserPublicProfile | null;
  role: string;
  joinedAt: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface ServerConversationMessage {
  id: string;
  channelId: string;
  authorUserId?: string | null;
  authorUser?: ServerUserPublicProfile | null;
  authorAgent?: ServerAgentItem | null;
  messageType: "user" | "system" | "task" | "event";
  content: Record<string, unknown>;
  textPreview?: string | null;
  threadRootMessageId?: string | null;
  replyCount: number;
  reactions: ServerConversationMessageReactionGroup[];
  createdAt: string;
  updatedAt: string;
}

export type ChannelMessageEntityKind =
  | "agent"
  | "user"
  | "artifact"
  | "task"
  | "message"
  | "thread";

export type ChannelMessageEntityAction = "trigger" | "mention" | "reference";

export interface ChannelMessageEntity {
  id: string;
  kind: ChannelMessageEntityKind;
  action: ChannelMessageEntityAction;
  targetId: string;
  displayText: string;
  insertedText: string;
  range?: {
    start: number;
    end: number;
  };
  metadata?: Record<string, unknown>;
}

export interface ChannelArtifactCandidate {
  artifactId: string;
  displayName: string;
  logicalPath: string;
  mimeType?: string | null;
  sizeBytes?: number | null;
  sourceKind: string;
  publishedByUserId?: string | null;
  publishedByAgentIdentityId?: string | null;
  publisher?: {
    actorType: "user" | "agent";
    userId?: string | null;
    agentIdentityId?: string | null;
    agentHandle?: string | null;
    label: string;
    avatarUrl?: string | null;
    visualKey?: string | null;
  } | null;
  createdAt?: string | null;
}

export interface ServerChannelEventContent {
  eventType: string;
  actorType?: "user" | "agent" | string | null;
  actorUserId?: string | null;
  actorLabel?: string | null;
  actorAgentIdentityId?: string | null;
  actorAgentHandle?: string | null;
  actorSessionId?: string | null;
  targetUserId?: string | null;
  targetAgentIdentityId?: string | null;
  targetAgentHandle?: string | null;
  targetLabel?: string | null;
  membershipId?: number | string | null;
  joinReason?: string | null;
  taskId?: string | null;
  taskNumber?: number | string | null;
  taskTitle?: string | null;
  title?: string | null;
  status?: string | null;
  priority?: string | null;
  commentText?: string | null;
  fromStatus?: string | null;
  toStatus?: string | null;
  fromAssignee?: unknown;
  toAssignee?: unknown;
  assignee?: unknown;
}

export interface ServerConversationMessageReactionActor {
  actorType: "user" | "agent";
  userId?: string | null;
  user?: ServerUserPublicProfile | null;
  agentIdentityId?: string | null;
  agentHandle?: string | null;
  agentLabel?: string | null;
}

export interface ServerConversationMessageReactionGroup {
  emoji: string;
  count: number;
  reactedByCurrentUser: boolean;
  reactedByCurrentAgent: boolean;
  actors: ServerConversationMessageReactionActor[];
}

export interface ServerExecutionTodoProgress {
  completed: number;
  total: number;
}

export interface ServerExecutionMessageContent {
  source: "agent_execution";
  session_id: string;
  run_id?: string | null;
  queue_item_id?: string | null;
  agent_identity_id?: string | null;
  agent_handle?: string | null;
  agent_label?: string | null;
  agent_visual_key?: string | null;
  trigger_message_id?: string | null;
  thread_root_message_id?: string | null;
  execution_status?: string | null;
  summary?: string | null;
  current_step?: string | null;
  todo_progress?: ServerExecutionTodoProgress | null;
}
