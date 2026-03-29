/**
 * Message parsing utilities for the Chat Service.
 *
 * Extracts the complex message-processing logic out of chat-service.ts
 * so the service file stays focused on API orchestration.
 */

import type {
  ChatMessage,
  MessageBlock,
  InputFile,
  ConfigSnapshot,
} from "@/features/chat/types";

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

interface MessageContentBlock {
  _type: string;
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  tool_use_id?: string;
  content?: string;
  is_error?: boolean;
  text?: string;
  thinking?: string;
  signature?: string;
}

interface MessageContentShape {
  _type?: string;
  subtype?: string;
  content?: MessageContentBlock[];
  text?: string;
  result?: string;
  parent_tool_use_id?: string | null;
}

export interface RawApiMessage {
  id: number;
  role: string;
  content: Record<string, unknown>;
  attachments?: InputFile[] | null;
  created_at: string;
  updated_at: string;
}

export interface ParsedMessages {
  messages: ChatMessage[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isLocalMountAccessMode(value: unknown): value is "ro" | "rw" {
  return value === "ro" || value === "rw";
}

function typeIncludes(typeValue: unknown, needle: string): boolean {
  if (!isNonEmptyString(typeValue)) return false;
  return typeValue === needle || typeValue.includes(needle);
}

/** Removes the Unicode replacement character (\uFFFD) from text. */
function cleanText(text: string): string {
  if (!text) return text;
  return text.replace(/\uFFFD/g, "");
}

function appendAssistantTextBlock(
  message: ChatMessage,
  text: string,
): ChatMessage {
  const normalized = text.trim();
  if (!normalized) return message;

  if (!Array.isArray(message.content)) {
    return {
      ...message,
      content: normalized,
    };
  }

  const existingBlocks = message.content as MessageBlock[];
  const lastTextBlock = [...existingBlocks]
    .reverse()
    .find((block) => block._type === "TextBlock");
  if (lastTextBlock?._type === "TextBlock") {
    const lastNormalized = cleanText(lastTextBlock.text).trim();
    if (lastNormalized === normalized) {
      return message;
    }
  }

  return {
    ...message,
    content: [...existingBlocks, { _type: "TextBlock", text: normalized }],
  };
}

// ---------------------------------------------------------------------------
// Config snapshot parser
// ---------------------------------------------------------------------------

export function parseConfigSnapshot(
  raw: Record<string, unknown> | null,
): ConfigSnapshot | null {
  if (!raw) return null;

  const parseIds = (arr: unknown): number[] | undefined =>
    Array.isArray(arr)
      ? arr.filter((id): id is number => typeof id === "number")
      : undefined;
  const parseLocalMounts = (
    mounts: unknown,
  ): ConfigSnapshot["local_mounts"] | undefined => {
    if (!Array.isArray(mounts)) return undefined;
    const parsed = mounts.flatMap((mount) => {
      if (!mount || typeof mount !== "object") return [];
      const rawMount = mount as Record<string, unknown>;
      if (
        !isNonEmptyString(rawMount.id) ||
        !isNonEmptyString(rawMount.name) ||
        !isNonEmptyString(rawMount.host_path)
      ) {
        return [];
      }
      return [
        {
          id: rawMount.id.trim(),
          name: rawMount.name.trim(),
          host_path: rawMount.host_path.trim(),
          access_mode: isLocalMountAccessMode(rawMount.access_mode)
            ? rawMount.access_mode
            : "ro",
        },
      ];
    });
    return parsed.length > 0 ? parsed : undefined;
  };

  return {
    mcp_server_ids: parseIds(raw.mcp_server_ids),
    skill_ids: parseIds(raw.skill_ids),
    plugin_ids: parseIds(raw.plugin_ids),
    model: isNonEmptyString(raw.model) ? raw.model.trim() : undefined,
    model_provider_id: isNonEmptyString(raw.model_provider_id)
      ? raw.model_provider_id.trim()
      : undefined,
    browser_enabled:
      typeof raw.browser_enabled === "boolean"
        ? raw.browser_enabled
        : undefined,
    memory_enabled:
      typeof raw.memory_enabled === "boolean" ? raw.memory_enabled : undefined,
    repo_url: isNonEmptyString(raw.repo_url) ? raw.repo_url.trim() : undefined,
    git_branch: isNonEmptyString(raw.git_branch)
      ? raw.git_branch.trim()
      : undefined,
    git_token_env_key: isNonEmptyString(raw.git_token_env_key)
      ? raw.git_token_env_key.trim()
      : undefined,
    filesystem_mode:
      raw.filesystem_mode === "local_mount" ? "local_mount" : "sandbox",
    local_mounts: parseLocalMounts(raw.local_mounts),
  };
}

// ---------------------------------------------------------------------------
// Main message parser
// ---------------------------------------------------------------------------

/**
 * Parses raw API messages into the UI-friendly `ChatMessage[]` format.
 *
 * This is the most complex piece of business logic in the chat feature.
 * It handles:
 * - Filtering system init messages
 * - Grouping tool use / result blocks into assistant messages
 * - Extracting thinking blocks
 * - Classifying real vs. internal user messages
 * - Attaching subagent transcripts to parent tool blocks
 */
export function parseMessages(
  rawMessages: RawApiMessage[],
  realUserMessageIds?: number[],
): ParsedMessages {
  const realUserMessageIdSet = new Set(realUserMessageIds ?? []);
  const canClassifyUserMessages = realUserMessageIdSet.size > 0;

  const processedMessages: ChatMessage[] = [];
  const subagentTranscriptByToolUseId: Record<string, string[]> = {};
  let currentAssistantMessage: ChatMessage | null = null;

  for (const msg of rawMessages) {
    const contentObj = msg.content as MessageContentShape;

    // Skip system init messages
    if (
      typeIncludes(contentObj._type, "SystemMessage") &&
      contentObj.subtype === "init"
    ) {
      continue;
    }

    const parentToolUseId = isNonEmptyString(contentObj.parent_tool_use_id)
      ? contentObj.parent_tool_use_id.trim()
      : null;

    // ---- Subagent messages (nested under a parent tool call) ----
    if (parentToolUseId) {
      const nestedTexts: string[] = [];
      if (isNonEmptyString(contentObj.text)) {
        nestedTexts.push(cleanText(contentObj.text));
      }
      if (Array.isArray(contentObj.content)) {
        for (const block of contentObj.content) {
          if (!typeIncludes(block?._type, "TextBlock")) continue;
          if (isNonEmptyString(block.text)) {
            nestedTexts.push(cleanText(block.text));
          }
        }
      }
      const cleaned = nestedTexts
        .map((t) => t.trim())
        .filter(Boolean)
        .join("\n\n");
      if (cleaned) {
        subagentTranscriptByToolUseId[parentToolUseId] = [
          ...(subagentTranscriptByToolUseId[parentToolUseId] || []),
          cleaned,
        ];
      }
      continue;
    }

    // ---- ToolUseBlock (assistant) ----
    if (msg.role === "assistant" && Array.isArray(contentObj.content)) {
      const toolUseBlocks = contentObj.content.filter((b) =>
        typeIncludes(b?._type, "ToolUseBlock"),
      );

      if (toolUseBlocks.length > 0) {
        if (!currentAssistantMessage) {
          currentAssistantMessage = {
            id: msg.id.toString(),
            role: "assistant",
            content: [],
            status: "completed",
            timestamp: msg.created_at,
          };
          processedMessages.push(currentAssistantMessage);
        }

        const existingBlocks =
          currentAssistantMessage.content as MessageBlock[];
        const uiToolBlocks = toolUseBlocks.map((b) => ({
          _type: "ToolUseBlock" as const,
          id: typeof b.id === "string" ? b.id : String(b.id ?? ""),
          name: typeof b.name === "string" ? b.name : String(b.name ?? ""),
          input:
            b.input && typeof b.input === "object"
              ? (b.input as Record<string, unknown>)
              : {},
        }));

        currentAssistantMessage.content = [...existingBlocks, ...uiToolBlocks];
      }
    }

    // ---- ToolResultBlock ----
    if (Array.isArray(contentObj.content)) {
      const toolResultBlocks = contentObj.content.filter((b) =>
        typeIncludes(b?._type, "ToolResultBlock"),
      );

      if (toolResultBlocks.length > 0) {
        if (!currentAssistantMessage) {
          currentAssistantMessage = {
            id: msg.id.toString(),
            role: "assistant",
            content: [],
            status: "completed",
            timestamp: msg.created_at,
          };
          processedMessages.push(currentAssistantMessage);
        }

        const uiResultBlocks = toolResultBlocks.map((b) => ({
          _type: "ToolResultBlock" as const,
          tool_use_id:
            typeof b.tool_use_id === "string"
              ? b.tool_use_id
              : String(b.tool_use_id ?? ""),
          content: cleanText(
            typeof b.content === "string"
              ? b.content
              : (JSON.stringify(b.content) ?? ""),
          ),
          is_error: !!b.is_error,
        }));

        const existingBlocks =
          currentAssistantMessage.content as MessageBlock[];
        currentAssistantMessage.content = [
          ...existingBlocks,
          ...uiResultBlocks,
        ];

        if (msg.role === "user") continue;
      }
    }

    // ---- ThinkingBlock (assistant) ----
    if (msg.role === "assistant" && Array.isArray(contentObj.content)) {
      const thinkingBlocks = contentObj.content.filter((b) =>
        typeIncludes(b?._type, "ThinkingBlock"),
      );

      const uiThinkingBlocks = thinkingBlocks
        .map((b) => ({
          _type: "ThinkingBlock" as const,
          thinking: cleanText(b.thinking || ""),
          signature: b.signature,
        }))
        .filter((b) => b.thinking.trim().length > 0);

      if (uiThinkingBlocks.length > 0) {
        if (!currentAssistantMessage) {
          currentAssistantMessage = {
            id: msg.id.toString(),
            role: "assistant",
            content: [],
            status: "completed",
            timestamp: msg.created_at,
          };
          processedMessages.push(currentAssistantMessage);
        }

        const existingBlocks =
          currentAssistantMessage.content as MessageBlock[];
        currentAssistantMessage.content = [
          ...existingBlocks,
          ...uiThinkingBlocks,
        ];
      }
    }

    // ---- Text content ----
    let textContent = "";
    if (isNonEmptyString(contentObj.text)) {
      textContent = cleanText(contentObj.text);
    } else if (
      typeIncludes(contentObj._type, "ResultMessage") &&
      isNonEmptyString(contentObj.result)
    ) {
      textContent = cleanText(contentObj.result);
    } else if (Array.isArray(contentObj.content)) {
      const textBlocks = contentObj.content
        .filter((b) => typeIncludes(b?._type, "TextBlock"))
        .map((b) => (isNonEmptyString(b.text) ? cleanText(b.text) : ""))
        .filter((t) => t.trim().length > 0);
      if (textBlocks.length > 0) textContent = textBlocks.join("\n\n");
    }

    if (textContent) {
      if (msg.role === "user") {
        const isRealUserMessage = canClassifyUserMessages
          ? realUserMessageIdSet.has(msg.id)
          : true;

        if (!isRealUserMessage) {
          continue;
        }

        currentAssistantMessage = null;
        processedMessages.push({
          id: msg.id.toString(),
          role: "user",
          content: textContent,
          status: "completed",
          timestamp: msg.created_at,
          attachments: msg.attachments ?? undefined,
        });
      } else {
        if (currentAssistantMessage) {
          currentAssistantMessage = appendAssistantTextBlock(
            currentAssistantMessage,
            textContent,
          );
          processedMessages[processedMessages.length - 1] =
            currentAssistantMessage;
        } else {
          processedMessages.push({
            id: msg.id.toString(),
            role: "assistant",
            content: textContent,
            status: "completed",
            timestamp: msg.created_at,
          });
        }
      }
    }
  }

  // Attach subagent transcripts to tool blocks
  for (const message of processedMessages) {
    if (message.role !== "assistant" || !Array.isArray(message.content))
      continue;
    message.content = (message.content as MessageBlock[]).map((block) => {
      if (block._type !== "ToolUseBlock") return block;
      const transcript = subagentTranscriptByToolUseId[block.id];
      if (!transcript || transcript.length === 0) return block;
      return { ...block, subagent_transcript: transcript };
    });
  }

  return { messages: processedMessages };
}
