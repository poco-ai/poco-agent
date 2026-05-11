import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type { FileNode } from "@/features/chat/types";
import type {
  ServerAgentItem,
  ServerChannelItem,
  ServerSystemChannelType,
  ServerChannelMemberItem,
  ServerChannelVisibility,
  ServerConversationMessage,
  ServerConversationMessageReactionActor,
  ServerConversationMessageReactionGroup,
  ServerConversationType,
  ServerInviteItem,
  ServerItem,
  ServerKind,
  ServerMemberItem,
  ServerRole,
  ServerUserPublicProfile,
} from "@/features/servers/model/types";
import {
  getServerMemberRolePath,
  getServerOwnershipTransferPath,
} from "@/features/servers/lib/server-member-api-paths";

interface ServerUserPublicProfileResponse {
  user_id: string;
  display_name?: string | null;
  avatar_url?: string | null;
}

interface ServerResponse {
  server_id: string;
  name: string;
  slug: string;
  kind: ServerKind;
  owner_user_id: string;
  created_at: string;
  updated_at: string;
}

interface ServerChannelResponse {
  channel_id: string;
  server_id: string;
  name: string;
  slug: string;
  description?: string | null;
  conversation_type: ServerConversationType;
  visibility: ServerChannelVisibility;
  system_channel_type?: ServerSystemChannelType | null;
  is_system_channel?: boolean;
  direct_user_id?: string | null;
  direct_agent_identity_id?: string | null;
  created_by: string | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ServerChannelMemberResponse {
  membership_id: number;
  channel_id: string;
  user_id: string;
  user?: ServerUserPublicProfileResponse | null;
  role: string;
  joined_at: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ServerAgentPersistentStateResponse {
  persistent_state_id: string;
  state_root_path: string;
  profile_path: string;
  memory_path: string;
  notes_dir_path: string;
  state_dir_path: string;
  artifacts_dir_path: string;
  state_version: number;
  runtime_status: string;
  active_task_id?: string | null;
  active_session_id?: string | null;
  last_synced_at?: string | null;
  last_written_at?: string | null;
}

interface ServerAgentResponse {
  agent_identity_id: string;
  server_id: string;
  preset_id: number;
  handle: string;
  display_name: string;
  description?: string | null;
  visual_key: string;
  visibility: string;
  lifecycle_state: string;
  created_by: string;
  updated_by?: string | null;
  removed_at?: string | null;
  removed_by?: string | null;
  persistent_state?: ServerAgentPersistentStateResponse | null;
  created_at: string;
  updated_at: string;
}

interface ServerMemberResponse {
  membership_id: number;
  server_id: string;
  user_id: string;
  user?: ServerUserPublicProfileResponse | null;
  role: ServerRole;
  joined_at: string;
  invited_by?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ServerInviteResponse {
  invite_id: string;
  server_id: string;
  token: string;
  role: ServerRole;
  expires_at: string;
  created_by: string;
  max_uses: number;
  used_count: number;
  revoked_at?: string | null;
  created_at: string;
  updated_at: string;
}

interface ServerConversationMessageResponse {
  message_id: string;
  channel_id: string;
  author_user_id?: string | null;
  author_user?: ServerUserPublicProfileResponse | null;
  author_agent?: ServerAgentResponse | null;
  message_type: "user" | "system" | "task" | "event";
  content: Record<string, unknown>;
  text_preview?: string | null;
  thread_root_message_id?: string | null;
  reply_count: number;
  reactions?: ServerConversationMessageReactionGroupResponse[];
  created_at: string;
  updated_at: string;
}

interface ServerConversationMessageReactionActorResponse {
  actor_type: "user" | "agent";
  user_id?: string | null;
  user?: ServerUserPublicProfileResponse | null;
  agent_identity_id?: string | null;
  agent_handle?: string | null;
  agent_label?: string | null;
}

interface ServerConversationMessageReactionGroupResponse {
  emoji: string;
  count: number;
  reacted_by_current_user: boolean;
  reacted_by_current_agent: boolean;
  actors?: ServerConversationMessageReactionActorResponse[];
}

interface ServerConversationThreadResponse {
  root: ServerConversationMessageResponse;
  replies: ServerConversationMessageResponse[];
}

function mapServer(server: ServerResponse): ServerItem {
  return {
    id: server.server_id,
    name: server.name,
    slug: server.slug,
    kind: server.kind,
    ownerUserId: server.owner_user_id,
    createdAt: server.created_at,
    updatedAt: server.updated_at,
  };
}

function mapUserProfile(
  profile?: ServerUserPublicProfileResponse | null,
): ServerUserPublicProfile | null {
  if (!profile) {
    return null;
  }
  return {
    userId: profile.user_id,
    displayName: profile.display_name,
    avatarUrl: profile.avatar_url,
  };
}

function mapChannel(channel: ServerChannelResponse): ServerChannelItem {
  return {
    id: channel.channel_id,
    serverId: channel.server_id,
    name: channel.name,
    slug: channel.slug,
    description: channel.description,
    conversationType: channel.conversation_type,
    visibility: channel.visibility,
    systemChannelType: channel.system_channel_type,
    isSystemChannel:
      channel.is_system_channel ?? channel.system_channel_type != null,
    directUserId: channel.direct_user_id,
    directAgentIdentityId: channel.direct_agent_identity_id,
    createdBy: channel.created_by,
    archivedAt: channel.archived_at,
    createdAt: channel.created_at,
    updatedAt: channel.updated_at,
  };
}

function mapChannelMember(
  member: ServerChannelMemberResponse,
): ServerChannelMemberItem {
  return {
    id: member.membership_id,
    channelId: member.channel_id,
    userId: member.user_id,
    user: mapUserProfile(member.user),
    role: member.role,
    joinedAt: member.joined_at,
    status: member.status,
    createdAt: member.created_at,
    updatedAt: member.updated_at,
  };
}

function mapAgent(agent: ServerAgentResponse): ServerAgentItem {
  return {
    id: agent.agent_identity_id,
    serverId: agent.server_id,
    presetId: agent.preset_id,
    handle: agent.handle,
    displayName: agent.display_name,
    description: agent.description,
    visualKey: agent.visual_key,
    visibility: agent.visibility,
    lifecycleState: agent.lifecycle_state,
    createdBy: agent.created_by,
    updatedBy: agent.updated_by,
    removedAt: agent.removed_at,
    removedBy: agent.removed_by,
    persistentState: agent.persistent_state
      ? {
          id: agent.persistent_state.persistent_state_id,
          stateRootPath: agent.persistent_state.state_root_path,
          profilePath: agent.persistent_state.profile_path,
          memoryPath: agent.persistent_state.memory_path,
          notesDirPath: agent.persistent_state.notes_dir_path,
          stateDirPath: agent.persistent_state.state_dir_path,
          artifactsDirPath: agent.persistent_state.artifacts_dir_path,
          stateVersion: agent.persistent_state.state_version,
          runtimeStatus: agent.persistent_state.runtime_status,
          activeTaskId: agent.persistent_state.active_task_id,
          activeSessionId: agent.persistent_state.active_session_id,
          lastSyncedAt: agent.persistent_state.last_synced_at,
          lastWrittenAt: agent.persistent_state.last_written_at,
        }
      : null,
    createdAt: agent.created_at,
    updatedAt: agent.updated_at,
  };
}

function mapServerMember(member: ServerMemberResponse): ServerMemberItem {
  return {
    id: member.membership_id,
    serverId: member.server_id,
    userId: member.user_id,
    user: mapUserProfile(member.user),
    role: member.role,
    joinedAt: member.joined_at,
    invitedBy: member.invited_by,
    status: member.status,
    createdAt: member.created_at,
    updatedAt: member.updated_at,
  };
}

function mapServerInvite(invite: ServerInviteResponse): ServerInviteItem {
  return {
    id: invite.invite_id,
    serverId: invite.server_id,
    token: invite.token,
    role: invite.role,
    expiresAt: invite.expires_at,
    createdBy: invite.created_by,
    maxUses: invite.max_uses,
    usedCount: invite.used_count,
    revokedAt: invite.revoked_at,
    createdAt: invite.created_at,
    updatedAt: invite.updated_at,
  };
}

function mapConversationMessage(
  message: ServerConversationMessageResponse,
): ServerConversationMessage {
  return {
    id: message.message_id,
    channelId: message.channel_id,
    authorUserId: message.author_user_id,
    authorUser: mapUserProfile(message.author_user),
    authorAgent: message.author_agent ? mapAgent(message.author_agent) : null,
    messageType: message.message_type,
    content: message.content,
    textPreview: message.text_preview,
    threadRootMessageId: message.thread_root_message_id,
    replyCount: message.reply_count,
    reactions: (message.reactions ?? []).map(mapReactionGroup),
    createdAt: message.created_at,
    updatedAt: message.updated_at,
  };
}

function mapReactionActor(
  actor: ServerConversationMessageReactionActorResponse,
): ServerConversationMessageReactionActor {
  return {
    actorType: actor.actor_type,
    userId: actor.user_id,
    user: mapUserProfile(actor.user),
    agentIdentityId: actor.agent_identity_id,
    agentHandle: actor.agent_handle,
    agentLabel: actor.agent_label,
  };
}

function mapReactionGroup(
  reaction: ServerConversationMessageReactionGroupResponse,
): ServerConversationMessageReactionGroup {
  return {
    emoji: reaction.emoji,
    count: reaction.count,
    reactedByCurrentUser: reaction.reacted_by_current_user,
    reactedByCurrentAgent: reaction.reacted_by_current_agent,
    actors: (reaction.actors ?? []).map(mapReactionActor),
  };
}

export const serversApi = {
  listServers: async (): Promise<ServerItem[]> => {
    const servers = await apiClient.get<ServerResponse[]>(
      API_ENDPOINTS.servers,
    );
    return servers.map(mapServer);
  },

  createServer: async (input: { name: string }): Promise<ServerItem> => {
    const server = await apiClient.post<ServerResponse>(API_ENDPOINTS.servers, {
      name: input.name,
    });
    return mapServer(server);
  },

  acceptInvite: async (input: { token: string }): Promise<ServerMemberItem> => {
    const member = await apiClient.post<ServerMemberResponse>(
      "/server-invites/accept",
      {
        token: input.token,
      },
    );
    return mapServerMember(member);
  },

  listMembers: async (serverId: string): Promise<ServerMemberItem[]> => {
    const members = await apiClient.get<ServerMemberResponse[]>(
      `/servers/${serverId}/members`,
    );
    return members.map(mapServerMember);
  },

  updateMemberRole: async (
    serverId: string,
    membershipId: number,
    role: ServerRole,
  ): Promise<ServerMemberItem> => {
    const member = await apiClient.patch<ServerMemberResponse>(
      getServerMemberRolePath(serverId, membershipId),
      { role },
    );
    return mapServerMember(member);
  },

  removeMember: async (
    serverId: string,
    membershipId: number,
  ): Promise<void> => {
    await apiClient.delete(`/servers/${serverId}/members/${membershipId}`);
  },

  transferOwnership: async (
    serverId: string,
    newOwnerUserId: string,
  ): Promise<ServerItem> => {
    const server = await apiClient.post<ServerResponse>(
      getServerOwnershipTransferPath(serverId),
      { new_owner_user_id: newOwnerUserId },
    );
    return mapServer(server);
  },

  listInvites: async (serverId: string): Promise<ServerInviteItem[]> => {
    const invites = await apiClient.get<ServerInviteResponse[]>(
      `/servers/${serverId}/invites`,
    );
    return invites.map(mapServerInvite);
  },

  listChannelArtifacts: async (
    serverId: string,
    channelId: string,
  ): Promise<FileNode[]> => {
    return apiClient.get<FileNode[]>(
      `/servers/${serverId}/channels/${channelId}/artifacts`,
    );
  },

  listAgentStateFiles: async (
    serverId: string,
    agentId: string,
  ): Promise<FileNode[]> => {
    return apiClient.get<FileNode[]>(
      `/servers/${serverId}/agents/${agentId}/state-files`,
    );
  },

  createInvite: async (
    serverId: string,
    input: {
      role?: string;
      expiresInDays?: number;
      maxUses?: number;
    } = {},
  ): Promise<ServerInviteItem> => {
    const invite = await apiClient.post<ServerInviteResponse>(
      `/servers/${serverId}/invites`,
      {
        role: input.role ?? "member",
        expires_in_days: input.expiresInDays ?? 30,
        max_uses: input.maxUses ?? 100,
      },
    );
    return mapServerInvite(invite);
  },

  createAgent: async (
    serverId: string,
    input: {
      displayName: string;
      handle?: string | null;
      description?: string | null;
      presetId: number;
      visualKey?: string | null;
    },
  ): Promise<ServerAgentItem> => {
    const agent = await apiClient.post<ServerAgentResponse>(
      `/servers/${serverId}/agents`,
      {
        display_name: input.displayName,
        handle: input.handle ?? null,
        description: input.description ?? null,
        preset_id: input.presetId,
        visual_key: input.visualKey ?? null,
        visibility: "server",
      },
    );
    return mapAgent(agent);
  },

  listChannels: async (serverId: string): Promise<ServerChannelItem[]> => {
    const channels = await apiClient.get<ServerChannelResponse[]>(
      API_ENDPOINTS.serverChannels(serverId),
    );
    return channels.map(mapChannel);
  },

  listAgents: async (serverId: string): Promise<ServerAgentItem[]> => {
    const agents = await apiClient.get<ServerAgentResponse[]>(
      `/servers/${serverId}/agents`,
    );
    return agents.map(mapAgent);
  },

  restartAgent: async (
    serverId: string,
    agentId: string,
  ): Promise<ServerAgentItem> => {
    const agent = await apiClient.post<ServerAgentResponse>(
      `/servers/${serverId}/agents/${agentId}/restart`,
    );
    return mapAgent(agent);
  },

  updateAgent: async (
    serverId: string,
    agentId: string,
    input: {
      description?: string | null;
    },
  ): Promise<ServerAgentItem> => {
    const agent = await apiClient.patch<ServerAgentResponse>(
      `/servers/${serverId}/agents/${agentId}`,
      {
        description: input.description ?? null,
      },
    );
    return mapAgent(agent);
  },

  stopAgent: async (
    serverId: string,
    agentId: string,
  ): Promise<ServerAgentItem> => {
    const agent = await apiClient.post<ServerAgentResponse>(
      `/servers/${serverId}/agents/${agentId}/stop`,
    );
    return mapAgent(agent);
  },

  removeAgent: async (serverId: string, agentId: string): Promise<void> => {
    await apiClient.delete(`/servers/${serverId}/agents/${agentId}`);
  },

  listChannelAgents: async (
    serverId: string,
    channelId: string,
  ): Promise<ServerAgentItem[]> => {
    const agents = await apiClient.get<ServerAgentResponse[]>(
      `/servers/${serverId}/channels/${channelId}/agents`,
    );
    return agents.map(mapAgent);
  },

  listMessages: async (
    serverId: string,
    channelId: string,
  ): Promise<ServerConversationMessage[]> => {
    const messages = await apiClient.get<ServerConversationMessageResponse[]>(
      `/servers/${serverId}/channels/${channelId}/messages`,
    );
    return messages.map(mapConversationMessage);
  },

  sendMessage: async (
    serverId: string,
    channelId: string,
    input: {
      text: string;
      threadRootMessageId?: string | null;
      asTask?: boolean;
    },
  ): Promise<ServerConversationMessage> => {
    const message = await apiClient.post<ServerConversationMessageResponse>(
      `/servers/${serverId}/channels/${channelId}/messages`,
      {
        message_type: "user",
        text_preview: input.text,
        thread_root_message_id: input.threadRootMessageId ?? null,
        content: {
          text: input.text,
          ...(input.asTask ? { as_task: true } : {}),
        },
      },
    );
    return mapConversationMessage(message);
  },

  getThread: async (
    serverId: string,
    channelId: string,
    threadRootMessageId: string,
  ): Promise<ServerConversationMessage[]> => {
    const thread = await apiClient.get<ServerConversationThreadResponse>(
      `/servers/${serverId}/channels/${channelId}/threads/${threadRootMessageId}`,
    );
    return [thread.root, ...thread.replies].map(mapConversationMessage);
  },

  addMessageReaction: async (
    serverId: string,
    channelId: string,
    messageId: string,
    emoji: string,
  ): Promise<void> => {
    await apiClient.post(
      `/servers/${serverId}/channels/${channelId}/messages/${messageId}/reactions`,
      { emoji },
    );
  },

  removeMessageReaction: async (
    serverId: string,
    channelId: string,
    messageId: string,
    emoji: string,
  ): Promise<void> => {
    await apiClient.delete(
      `/servers/${serverId}/channels/${channelId}/messages/${messageId}/reactions`,
      { body: { emoji } as unknown as BodyInit },
    );
  },

  createDirectMessage: async (
    serverId: string,
    input: {
      targetUserId?: string | null;
      targetAgentIdentityId?: string | null;
    },
  ): Promise<ServerChannelItem> => {
    const channel = await apiClient.post<ServerChannelResponse>(
      `/servers/${serverId}/direct-messages`,
      {
        target_user_id: input.targetUserId ?? null,
        target_agent_identity_id: input.targetAgentIdentityId ?? null,
      },
    );
    return mapChannel(channel);
  },

  createChannel: async (
    serverId: string,
    input: {
      name: string;
      description?: string | null;
      visibility?: ServerChannelVisibility;
      memberUserIds?: string[];
      agentIdentityIds?: string[];
    },
  ): Promise<ServerChannelItem> => {
    const channel = await apiClient.post<ServerChannelResponse>(
      API_ENDPOINTS.serverChannels(serverId),
      {
        name: input.name,
        description: input.description ?? null,
        visibility: input.visibility ?? "public",
        member_user_ids: input.memberUserIds ?? [],
        agent_identity_ids: input.agentIdentityIds ?? [],
      },
    );
    return mapChannel(channel);
  },

  updateChannel: async (
    serverId: string,
    channelId: string,
    input: {
      name?: string | null;
      description?: string | null;
    },
  ): Promise<ServerChannelItem> => {
    const channel = await apiClient.patch<ServerChannelResponse>(
      `/servers/${serverId}/channels/${channelId}`,
      input,
    );
    return mapChannel(channel);
  },

  archiveChannel: async (
    serverId: string,
    channelId: string,
  ): Promise<ServerChannelItem> => {
    const channel = await apiClient.post<ServerChannelResponse>(
      `/servers/${serverId}/channels/${channelId}/archive`,
    );
    return mapChannel(channel);
  },

  deleteChannel: async (serverId: string, channelId: string): Promise<void> => {
    await apiClient.delete(`/servers/${serverId}/channels/${channelId}`);
  },

  listChannelMembers: async (
    serverId: string,
    channelId: string,
  ): Promise<ServerChannelMemberItem[]> => {
    const members = await apiClient.get<ServerChannelMemberResponse[]>(
      `/servers/${serverId}/channels/${channelId}/members`,
    );
    return members.map(mapChannelMember);
  },

  addChannelMember: async (
    serverId: string,
    channelId: string,
    input: {
      userId: string;
      role?: string;
    },
  ): Promise<ServerChannelMemberItem> => {
    const member = await apiClient.post<ServerChannelMemberResponse>(
      `/servers/${serverId}/channels/${channelId}/members`,
      {
        user_id: input.userId,
        role: input.role ?? "member",
      },
    );
    return mapChannelMember(member);
  },

  removeChannelMember: async (
    serverId: string,
    channelId: string,
    membershipId: number,
  ): Promise<void> => {
    await apiClient.delete(
      `/servers/${serverId}/channels/${channelId}/members/${membershipId}`,
    );
  },

  addAgentToChannel: async (
    serverId: string,
    channelId: string,
    input: {
      agentIdentityId: string;
      role?: string;
    },
  ): Promise<void> => {
    await apiClient.post(`/servers/${serverId}/channels/${channelId}/agents`, {
      agent_identity_id: input.agentIdentityId,
      role: input.role ?? "member",
    });
  },

  removeAgentFromChannel: async (
    serverId: string,
    channelId: string,
    agentId: string,
  ): Promise<void> => {
    await apiClient.delete(
      `/servers/${serverId}/channels/${channelId}/agents/${agentId}`,
    );
  },

  leaveChannel: async (serverId: string, channelId: string): Promise<void> => {
    await apiClient.post(`/servers/${serverId}/channels/${channelId}/leave`);
  },
};
