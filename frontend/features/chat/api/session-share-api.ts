import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  ConversationTimelineItem,
  FileChange,
  FileNode,
  MessageResponse,
  SessionShareForkResponse,
  SessionSharePublicResponse,
  SessionShareResponse,
  SessionShareSnapshot,
  SessionShareToChannelResponse,
  SharedRunSummary,
  SharedSessionSummary,
  SharedToolExecution,
} from "@/features/chat/types";

interface SessionShareResponseDto {
  share_id: string;
  source_session_id: string;
  token: string;
  title?: string | null;
  description?: string | null;
  is_revoked: boolean;
  created_at: string;
  updated_at: string;
}

interface SessionSharePublicResponseDto {
  share_id: string;
  title?: string | null;
  description?: string | null;
  created_at: string;
  updated_at: string;
}

interface SharedSessionSummaryDto {
  session_id: string;
  title?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface SharedToolExecutionDto {
  id: string;
  run_id?: string | null;
  message_id?: number | null;
  tool_use_id?: string | null;
  tool_name: string;
  tool_input?: Record<string, unknown> | null;
  tool_output?: Record<string, unknown> | null;
  is_error: boolean;
  duration_ms?: number | null;
  browser_screenshot_url?: string | null;
  created_at: string;
  updated_at: string;
}

interface SharedRunSummaryDto {
  run_id: string;
  user_message_id: number;
  status: string;
  progress: number;
  schedule_mode: string;
  workspace_export_status?: string | null;
  replay_step_count: number;
  file_change_count: number;
  file_changes?: FileChange[];
  workspace_files?: FileNode[];
  tool_executions?: SharedToolExecutionDto[];
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  updated_at: string;
}

interface ConversationTimelineItemDto {
  id: string;
  item_type: ConversationTimelineItem["itemType"];
  label: string;
  status?: string | null;
  role?: string | null;
  message_id?: number | null;
  run_id?: string | null;
  channel_message_id?: string | null;
  source_message_id?: number | null;
  source_run_id?: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

interface SessionShareSnapshotDto {
  share: SessionSharePublicResponseDto;
  session: SharedSessionSummaryDto;
  messages: MessageResponse[];
  runs: SharedRunSummaryDto[];
  timeline: ConversationTimelineItemDto[];
}

interface SessionShareForkResponseDto {
  session_id: string;
  source_session_id: string;
  share_id: string;
}

interface SessionShareToChannelResponseDto {
  share_id: string;
  source_session_id: string;
  thread: {
    root: {
      message_id: string;
      channel_id: string;
    };
  };
}

function mapShare(dto: SessionShareResponseDto): SessionShareResponse {
  return {
    shareId: dto.share_id,
    sourceSessionId: dto.source_session_id,
    token: dto.token,
    title: dto.title,
    description: dto.description,
    isRevoked: dto.is_revoked,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapPublicShare(
  dto: SessionSharePublicResponseDto,
): SessionSharePublicResponse {
  return {
    shareId: dto.share_id,
    title: dto.title,
    description: dto.description,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapSession(dto: SharedSessionSummaryDto): SharedSessionSummary {
  return {
    sessionId: dto.session_id,
    title: dto.title,
    status: dto.status,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapToolExecution(dto: SharedToolExecutionDto): SharedToolExecution {
  return {
    id: dto.id,
    runId: dto.run_id,
    messageId: dto.message_id,
    toolUseId: dto.tool_use_id,
    toolName: dto.tool_name,
    toolInput: dto.tool_input,
    toolOutput: dto.tool_output,
    isError: dto.is_error,
    durationMs: dto.duration_ms,
    browserScreenshotUrl: dto.browser_screenshot_url,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapRun(dto: SharedRunSummaryDto): SharedRunSummary {
  return {
    runId: dto.run_id,
    userMessageId: dto.user_message_id,
    status: dto.status,
    progress: dto.progress,
    scheduleMode: dto.schedule_mode,
    workspaceExportStatus: dto.workspace_export_status,
    replayStepCount: dto.replay_step_count,
    fileChangeCount: dto.file_change_count,
    fileChanges: dto.file_changes ?? [],
    workspaceFiles: dto.workspace_files ?? [],
    toolExecutions: (dto.tool_executions ?? []).map(mapToolExecution),
    startedAt: dto.started_at,
    finishedAt: dto.finished_at,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function mapTimelineItem(
  dto: ConversationTimelineItemDto,
): ConversationTimelineItem {
  return {
    id: dto.id,
    itemType: dto.item_type,
    label: dto.label,
    status: dto.status,
    role: dto.role,
    messageId: dto.message_id,
    runId: dto.run_id,
    channelMessageId: dto.channel_message_id,
    sourceMessageId: dto.source_message_id,
    sourceRunId: dto.source_run_id,
    createdAt: dto.created_at,
    metadata: dto.metadata ?? {},
  };
}

function mapSnapshot(dto: SessionShareSnapshotDto): SessionShareSnapshot {
  return {
    share: mapPublicShare(dto.share),
    session: mapSession(dto.session),
    messages: dto.messages,
    runs: dto.runs.map(mapRun),
    timeline: dto.timeline.map(mapTimelineItem),
  };
}

export const sessionShareApi = {
  createShare: async (
    sessionId: string,
    input: { title?: string | null; description?: string | null } = {},
  ): Promise<SessionShareResponse> => {
    const share = await apiClient.post<SessionShareResponseDto>(
      API_ENDPOINTS.sessionShareCreate(sessionId),
      {
        title: input.title ?? null,
        description: input.description ?? null,
      },
    );
    return mapShare(share);
  },

  getSnapshot: async (token: string): Promise<SessionShareSnapshot> => {
    const snapshot = await apiClient.get<SessionShareSnapshotDto>(
      API_ENDPOINTS.sessionShare(token),
    );
    return mapSnapshot(snapshot);
  },

  forkShare: async (token: string): Promise<SessionShareForkResponse> => {
    const result = await apiClient.post<SessionShareForkResponseDto>(
      API_ENDPOINTS.sessionShareFork(token),
    );
    return {
      sessionId: result.session_id,
      sourceSessionId: result.source_session_id,
      shareId: result.share_id,
    };
  },

  shareToChannel: async (
    token: string,
    input: {
      serverId: string;
      channelId: string;
      title?: string | null;
    },
  ): Promise<SessionShareToChannelResponse> => {
    const result = await apiClient.post<SessionShareToChannelResponseDto>(
      API_ENDPOINTS.sessionShareToChannel(token),
      {
        server_id: input.serverId,
        channel_id: input.channelId,
        title: input.title ?? null,
      },
    );
    return {
      shareId: result.share_id,
      sourceSessionId: result.source_session_id,
      rootMessageId: result.thread.root.message_id,
      channelId: result.thread.root.channel_id,
    };
  },
};
