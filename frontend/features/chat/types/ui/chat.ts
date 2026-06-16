import type {
  ChatFileReference,
  ChatSkillReference,
  InputFile,
} from "../api/session";

/**
 * Chat-related UI types (frontend-specific)
 */

export type MessageRole = "user" | "assistant" | "system";

export type MessageStatus =
  | "sending"
  | "sent"
  | "streaming"
  | "completed"
  | "failed";

export type TextBlock = {
  _type: "TextBlock";
  text: string;
};

export type ThinkingBlock = {
  _type: "ThinkingBlock";
  thinking: string;
  signature?: string;
};

export type ToolUseBlock = {
  _type: "ToolUseBlock";
  id: string;
  name: string;
  input: Record<string, unknown>;
  // When the tool spawns a subagent (e.g., Task), we attach a flattened transcript here.
  subagent_transcript?: string[];
};

export type ToolResultBlock = {
  _type: "ToolResultBlock";
  tool_use_id: string;
  content: string;
  is_error: boolean;
};

export type MessageBlock =
  | TextBlock
  | ThinkingBlock
  | ToolUseBlock
  | ToolResultBlock;

export type ToolCall = {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: string;
  status: "pending" | "running" | "completed" | "failed";
};

export type AgentTriggerContext = {
  version?: number;
  trigger_type?: string;
  server_id?: string;
  channel_id?: string;
  trigger_message_id?: string;
  thread_root_message_id?: string | null;
  target_agent_identity_id?: string;
  target_agent_handle?: string;
  source_actor?: {
    actor_type?: string;
    user_id?: string | null;
    agent_identity_id?: string | null;
    display_name?: string | null;
  };
  references?: {
    message_ids?: string[];
    artifact_ids?: string[];
    task_ids?: string[];
  };
  handoff?: {
    parent_run_id?: string | null;
    depth?: number;
    dedupe_key?: string | null;
  };
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string | MessageBlock[];
  status: MessageStatus;
  timestamp?: string;
  metadata?: {
    model?: string;
    tokensUsed?: number;
    duration?: number;
    toolCalls?: ToolCall[];
    triggerContext?: AgentTriggerContext;
    fileReferences?: ChatFileReference[];
    inputFileReferences?: ChatFileReference[];
    skillReferences?: ChatSkillReference[];
  };
  parentId?: string;
  attachments?: InputFile[];
};

export type ChatSession = {
  id: string;
  taskId: string;
  title: string;
  messages: ChatMessage[];
  status:
    | "pending"
    | "running"
    | "canceling"
    | "completed"
    | "failed"
    | "canceled";
  model: string;
  createdAt: string;
  updatedAt: string;
};
