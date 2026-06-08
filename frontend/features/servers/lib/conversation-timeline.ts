import type { ConversationTimelineItem } from "@/features/chat/types";
import type { ServerConversationMessage } from "@/features/servers/model/types";

function getString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function buildLabel(message: ServerConversationMessage): string {
  return (
    message.textPreview ||
    getString(message.content.text) ||
    getString(message.content.body) ||
    message.messageType
  );
}

export function buildChannelTimelineItems(
  messages: ServerConversationMessage[],
): ConversationTimelineItem[] {
  return messages.map((message) => {
    const source = getString(message.content.source);
    const sourceMessageId = message.content.source_message_id;
    const sourceRunId = getString(message.content.source_run_id);
    return {
      id: `channel-message:${message.id}`,
      itemType:
        message.messageType === "event" ? "channel_event" : "channel_message",
      label: buildLabel(message),
      status: getString(message.content.execution_status),
      role: getString(message.content.source_role),
      channelMessageId: message.id,
      sourceMessageId:
        typeof sourceMessageId === "number" ? sourceMessageId : null,
      sourceRunId,
      createdAt: message.createdAt,
      metadata: {
        source,
        messageType: message.messageType,
      },
    };
  });
}
