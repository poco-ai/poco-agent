import type {
  ServerAgentItem,
  ServerChannelMemberItem,
  ServerConversationMessage,
  ServerMemberItem,
  ServerUserPublicProfile,
} from "@/features/servers/model/types";

export interface MentionCandidate {
  id: string;
  label: string;
  handle: string;
  kind: "agent" | "human";
  description?: string | null;
}

function normalizeMentionSearch(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function hasWhitespace(value: string): boolean {
  return /\s/u.test(value);
}

export function getUserDisplayName(
  profile: ServerUserPublicProfile | null | undefined,
  fallbackUserId?: string | null,
): string {
  const displayName = profile?.displayName?.trim();
  if (displayName) {
    return displayName;
  }
  return fallbackUserId?.trim() || "User";
}

export function getUserAvatarUrl(
  profile: ServerUserPublicProfile | null | undefined,
): string | null {
  const avatarUrl = profile?.avatarUrl?.trim();
  return avatarUrl || null;
}

function getMessageTimestamp(message: ServerConversationMessage): number {
  const timestamp = Date.parse(message.createdAt);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

export function sortMessagesChronologically(
  messages: ServerConversationMessage[],
): ServerConversationMessage[] {
  return [...messages].sort((left, right) => {
    const timestampDiff =
      getMessageTimestamp(left) - getMessageTimestamp(right);
    if (timestampDiff !== 0) {
      return timestampDiff;
    }
    return left.id.localeCompare(right.id);
  });
}

export function getMentionTrigger(
  value: string,
): { start: number; query: string } | null {
  const match = value.match(/(?:^|\s)@([^\s@]*)$/u);
  if (!match || match.index === undefined) {
    return null;
  }
  return {
    start: match.index + match[0].lastIndexOf("@"),
    query: normalizeMentionSearch(match[1]),
  };
}

export function buildAgentMentionCandidate(
  agent: ServerAgentItem,
): MentionCandidate {
  return {
    id: agent.id,
    label: agent.displayName,
    handle: agent.handle,
    kind: "agent",
    description: agent.description,
  };
}

export function getMentionSearchText(candidate: MentionCandidate): string {
  return normalizeMentionSearch(`${candidate.label} ${candidate.handle}`);
}

export function getMentionInsertText(candidate: MentionCandidate): string {
  if (candidate.kind === "agent") {
    const label = candidate.label.trim();
    if (label && !hasWhitespace(label)) {
      return `@${label} `;
    }
  }
  return `@${candidate.handle} `;
}

export function buildHumanMentionCandidates(
  members: ServerChannelMemberItem[],
  currentUserId?: string | null,
): MentionCandidate[] {
  const excludedUserId = currentUserId?.trim();
  return members
    .filter((member) => !excludedUserId || member.userId !== excludedUserId)
    .map((member) => ({
      id: member.userId,
      label: getUserDisplayName(member.user, member.userId),
      handle: member.userId,
      kind: "human",
    }));
}

export function getAvailableChannelHumanMembers(
  serverMembers: ServerMemberItem[],
  channelMembers: ServerChannelMemberItem[],
): ServerMemberItem[] {
  const activeChannelUserIds = new Set(
    channelMembers
      .filter((member) => member.status === "active")
      .map((member) => member.userId),
  );
  return serverMembers.filter(
    (member) =>
      member.status === "active" && !activeChannelUserIds.has(member.userId),
  );
}

export function messageMentionsUser(
  message: ServerConversationMessage,
  userId?: string | null,
): boolean {
  const normalizedUserId = userId?.trim();
  if (!normalizedUserId) {
    return false;
  }

  const text =
    typeof message.content.text === "string"
      ? message.content.text
      : (message.textPreview ?? "");
  const mentionPattern = new RegExp(
    `(^|\\s)@${normalizedUserId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?=$|\\s|[,.!?;:])`,
    "iu",
  );
  return mentionPattern.test(text);
}

export function hasInboxSignal(
  message: ServerConversationMessage,
  userId?: string | null,
): boolean {
  return messageMentionsUser(message, userId) || message.replyCount > 0;
}
