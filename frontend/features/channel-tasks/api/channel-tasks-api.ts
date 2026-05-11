import { API_ENDPOINTS, apiClient } from "@/services/api-client";

import type {
  ChannelTaskActivityMessage,
  ChannelTask,
  ChannelTaskActorSummary,
  ChannelTaskCreateInput,
  ChannelTaskMessageContext,
  ChannelTaskStatusUpdateInput,
  ChannelTaskStatus,
  ChannelTaskUpdateInput,
} from "../model/types";

interface ChannelTaskResponse {
  task_id: string;
  server_id: string;
  channel_id: string;
  display_number: number;
  title: string;
  description?: string | null;
  status: ChannelTaskStatus;
  position: number;
  priority?: string | null;
  due_date?: string | null;
  assignee_user_id?: string | null;
  assignee_preset_id?: number | null;
  assignee_agent_identity_id?: string | null;
  creator?: ChannelTaskActorSummaryResponse | null;
  assignee?: ChannelTaskActorSummaryResponse | null;
  reporter_user_id?: string | null;
  related_project_id?: string | null;
  creator_user_id: string;
  updated_by?: string | null;
  thread_root_message_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface ChannelTaskActorSummaryResponse {
  actor_type: "user" | "agent";
  user_id?: string | null;
  agent_identity_id?: string | null;
  agent_handle?: string | null;
  label: string;
  avatar_url?: string | null;
  visual_key?: string | null;
}

function mapActorSummary(
  summary?: ChannelTaskActorSummaryResponse | null,
): ChannelTaskActorSummary | null {
  if (!summary) {
    return null;
  }
  return {
    actorType: summary.actor_type,
    userId: summary.user_id,
    agentIdentityId: summary.agent_identity_id,
    agentHandle: summary.agent_handle,
    label: summary.label,
    avatarUrl: summary.avatar_url,
    visualKey: summary.visual_key,
  };
}

function mapTask(task: ChannelTaskResponse): ChannelTask {
  return {
    taskId: task.task_id,
    serverId: task.server_id,
    channelId: task.channel_id,
    displayNumber: task.display_number,
    title: task.title,
    description: task.description,
    status: task.status,
    position: task.position,
    priority: task.priority,
    dueDate: task.due_date,
    assigneeUserId: task.assignee_user_id,
    assigneePresetId: task.assignee_preset_id,
    assigneeAgentIdentityId: task.assignee_agent_identity_id,
    creator: mapActorSummary(task.creator),
    assignee: mapActorSummary(task.assignee),
    reporterUserId: task.reporter_user_id,
    relatedProjectId: task.related_project_id,
    creatorUserId: task.creator_user_id,
    updatedBy: task.updated_by,
    threadRootMessageId: task.thread_root_message_id,
    createdAt: task.created_at,
    updatedAt: task.updated_at,
  };
}

interface ChannelTaskMessageResponse {
  message_id: string;
  channel_id: string;
  author_user_id?: string | null;
  message_type: "user" | "system" | "task" | "event";
  content: Record<string, unknown>;
  text_preview?: string | null;
  thread_root_message_id?: string | null;
  created_at: string;
  updated_at: string;
}

interface ChannelTaskThreadResponse {
  root: ChannelTaskMessageResponse;
  replies: ChannelTaskMessageResponse[];
}

interface ChannelTaskMessageContextResponse {
  target: ChannelTaskMessageResponse;
  messages: ChannelTaskMessageResponse[];
}

function mapActivityMessage(
  message: ChannelTaskMessageResponse,
): ChannelTaskActivityMessage {
  return {
    messageId: message.message_id,
    channelId: message.channel_id,
    authorUserId: message.author_user_id,
    messageType: message.message_type,
    content: message.content,
    textPreview: message.text_preview,
    threadRootMessageId: message.thread_root_message_id,
    createdAt: message.created_at,
    updatedAt: message.updated_at,
  };
}

export const channelTasksApi = {
  listTasks: async (
    serverId: string,
    channelId: string,
  ): Promise<ChannelTask[]> => {
    const tasks = await apiClient.get<ChannelTaskResponse[]>(
      API_ENDPOINTS.serverChannelTasks(serverId, channelId),
    );
    return tasks.map(mapTask);
  },

  createTask: async (
    serverId: string,
    channelId: string,
    input: ChannelTaskCreateInput,
  ): Promise<ChannelTask> => {
    const task = await apiClient.post<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTasks(serverId, channelId),
      {
        title: input.title,
        description: input.description,
        priority: input.priority,
        source_message_id: input.sourceMessageId ?? null,
      },
    );
    return mapTask(task);
  },

  getTask: async (
    serverId: string,
    channelId: string,
    taskId: string,
  ): Promise<ChannelTask> => {
    const task = await apiClient.get<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTask(serverId, channelId, taskId),
    );
    return mapTask(task);
  },

  updateTask: async (
    serverId: string,
    channelId: string,
    taskId: string,
    input: ChannelTaskUpdateInput,
  ): Promise<ChannelTask> => {
    const task = await apiClient.patch<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTask(serverId, channelId, taskId),
      {
        title: input.title,
        description: input.description,
        priority: input.priority,
        assignee_user_id: input.assigneeUserId,
        assignee_preset_id: input.assigneePresetId,
        assignee_agent_identity_id: input.assigneeAgentIdentityId,
      },
    );
    return mapTask(task);
  },

  updateTaskStatus: async (
    serverId: string,
    channelId: string,
    taskId: string,
    input: ChannelTaskStatusUpdateInput,
  ): Promise<ChannelTask> => {
    const task = await apiClient.post<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTaskStatus(serverId, channelId, taskId),
      input,
    );
    return mapTask(task);
  },

  claimTask: async (
    serverId: string,
    channelId: string,
    taskId: string,
  ): Promise<ChannelTask> => {
    const task = await apiClient.post<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTaskClaim(serverId, channelId, taskId),
      {},
    );
    return mapTask(task);
  },

  unclaimTask: async (
    serverId: string,
    channelId: string,
    taskId: string,
  ): Promise<ChannelTask> => {
    const task = await apiClient.post<ChannelTaskResponse>(
      API_ENDPOINTS.serverChannelTaskUnclaim(serverId, channelId, taskId),
      {},
    );
    return mapTask(task);
  },

  getTaskThread: async (
    serverId: string,
    channelId: string,
    threadRootMessageId: string,
  ): Promise<ChannelTaskActivityMessage[]> => {
    const thread = await apiClient.get<ChannelTaskThreadResponse>(
      API_ENDPOINTS.serverChannelThread(
        serverId,
        channelId,
        threadRootMessageId,
      ),
    );
    return [thread.root, ...thread.replies].map(mapActivityMessage);
  },

  getMessageContext: async (
    serverId: string,
    channelId: string,
    messageId: string,
  ): Promise<ChannelTaskMessageContext> => {
    const context = await apiClient.get<ChannelTaskMessageContextResponse>(
      `${API_ENDPOINTS.serverChannelMessageContext(
        serverId,
        channelId,
        messageId,
      )}?before=20&after=20`,
    );
    return {
      target: mapActivityMessage(context.target),
      messages: context.messages.map(mapActivityMessage),
    };
  },
};
