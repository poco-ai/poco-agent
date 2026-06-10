import type { FileChange } from "./callback";
import type { FileNode } from "./file";
import type { MessageResponse } from "./session";

export type ConversationTimelineItemType =
  | "message"
  | "run"
  | "channel_message"
  | "channel_event";

export interface ConversationTimelineItem {
  id: string;
  itemType: ConversationTimelineItemType;
  label: string;
  status?: string | null;
  role?: string | null;
  messageId?: number | null;
  runId?: string | null;
  channelMessageId?: string | null;
  sourceMessageId?: number | null;
  sourceRunId?: string | null;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface SessionShareResponse {
  shareId: string;
  sourceSessionId: string;
  token: string;
  title?: string | null;
  description?: string | null;
  isRevoked: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SessionSharePublicResponse {
  shareId: string;
  title?: string | null;
  description?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SharedSessionSummary {
  sessionId: string;
  title?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface SharedToolExecution {
  id: string;
  runId?: string | null;
  messageId?: number | null;
  toolUseId?: string | null;
  toolName: string;
  toolInput?: Record<string, unknown> | null;
  toolOutput?: Record<string, unknown> | null;
  isError: boolean;
  durationMs?: number | null;
  browserScreenshotUrl?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SharedRunSummary {
  runId: string;
  userMessageId: number;
  status: string;
  progress: number;
  scheduleMode: string;
  workspaceExportStatus?: string | null;
  replayStepCount: number;
  fileChangeCount: number;
  fileChanges: FileChange[];
  workspaceFiles: FileNode[];
  toolExecutions: SharedToolExecution[];
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface SessionShareSnapshot {
  share: SessionSharePublicResponse;
  session: SharedSessionSummary;
  messages: MessageResponse[];
  runs: SharedRunSummary[];
  timeline: ConversationTimelineItem[];
}

export interface SessionShareForkResponse {
  sessionId: string;
  sourceSessionId: string;
  shareId: string;
}

export interface SessionShareToChannelResponse {
  shareId: string;
  sourceSessionId: string;
  rootMessageId: string;
  channelId: string;
}
