import type {
  ChannelArtifactCandidate,
  ChannelMessageEntity,
  ChannelMessageEntityAction,
  ChannelMessageEntityKind,
  ServerAgentItem,
  ServerChannelItem,
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

export interface ComposerTrigger {
  prefix: "@" | "#";
  start: number;
  query: string;
}

export interface ComposerCandidate {
  id: string;
  label: string;
  kind: ChannelMessageEntityKind;
  action: ChannelMessageEntityAction;
  targetId: string;
  insertedText: string;
  metaLabel?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown>;
}

function normalizeMentionSearch(value: string): string {
  return value.trim().toLocaleLowerCase();
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

function getChannelSortRank(channel: ServerChannelItem): number {
  if (channel.systemChannelType === "personal") {
    return 0;
  }
  if (channel.systemChannelType === "public") {
    return 1;
  }
  return 2;
}

export function sortChannelsForSidebar(
  channels: ServerChannelItem[],
): ServerChannelItem[] {
  return [...channels].sort((left, right) => {
    const rankDiff = getChannelSortRank(left) - getChannelSortRank(right);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    const createdDiff =
      Date.parse(left.createdAt || "") - Date.parse(right.createdAt || "");
    if (!Number.isNaN(createdDiff) && createdDiff !== 0) {
      return createdDiff;
    }
    return left.name.localeCompare(right.name);
  });
}

export function getMentionTrigger(
  value: string,
): { start: number; query: string } | null {
  const trigger = getComposerTrigger(value);
  if (!trigger || trigger.prefix !== "@") {
    return null;
  }
  return {
    start: trigger.start,
    query: trigger.query,
  };
}

export function getComposerTrigger(value: string): ComposerTrigger | null {
  const match = value.match(/(?:^|\s)([@#])([^\s@#]*)$/u);
  if (!match || match.index === undefined) {
    return null;
  }
  const prefix = match[1] === "#" ? "#" : "@";
  return {
    prefix,
    start: match.index + match[0].lastIndexOf(prefix),
    query: normalizeMentionSearch(match[2]),
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
  return `@${candidate.handle} `;
}

export function buildParticipantComposerCandidate(
  candidate: MentionCandidate,
): ComposerCandidate {
  const insertedText = getMentionInsertText(candidate).trimEnd();
  return {
    id: `${candidate.kind}-${candidate.id}`,
    label: candidate.label,
    kind: candidate.kind === "agent" ? "agent" : "user",
    action: candidate.kind === "agent" ? "trigger" : "mention",
    targetId: candidate.id,
    insertedText,
    metaLabel: `@${candidate.handle}`,
    description: candidate.description,
    metadata: { handle: candidate.handle },
  };
}

export function buildArtifactComposerCandidate(
  artifact: ChannelArtifactCandidate,
): ComposerCandidate {
  return {
    id: `artifact-${artifact.artifactId}`,
    label: artifact.displayName,
    kind: "artifact",
    action: "reference",
    targetId: artifact.artifactId,
    insertedText: `#${artifact.displayName}`,
    metaLabel: artifact.logicalPath,
    metadata: {
      logical_path: artifact.logicalPath,
      mime_type: artifact.mimeType,
      size_bytes: artifact.sizeBytes,
      source_kind: artifact.sourceKind,
    },
  };
}

export function buildTaskComposerCandidate(task: {
  taskId: string;
  displayNumber: number;
  title: string;
  status: string;
}): ComposerCandidate {
  return {
    id: `task-${task.taskId}`,
    label: task.title,
    kind: "task",
    action: "reference",
    targetId: task.taskId,
    insertedText: `#task-${task.displayNumber}`,
    metaLabel: `#task-${task.displayNumber} / ${task.status.replaceAll("_", " ")}`,
    metadata: {
      display_number: task.displayNumber,
      title: task.title,
      status: task.status,
    },
  };
}

export function getComposerCandidateSearchText(
  candidate: ComposerCandidate,
): string {
  return normalizeMentionSearch(
    `${candidate.label} ${candidate.insertedText} ${candidate.metaLabel ?? ""}`,
  );
}

export function insertComposerCandidate(
  draft: string,
  trigger: ComposerTrigger,
  candidate: ComposerCandidate,
): { text: string; entity: ChannelMessageEntity } {
  const insertText = `${candidate.insertedText} `;
  const replaceEnd = trigger.start + trigger.query.length + 1;
  const text = `${draft.slice(0, trigger.start)}${insertText}${draft.slice(replaceEnd)}`;
  return {
    text,
    entity: {
      id: `${candidate.id}-${Date.now()}`,
      kind: candidate.kind,
      action: candidate.action,
      targetId: candidate.targetId,
      displayText: candidate.label,
      insertedText: candidate.insertedText,
      range: {
        start: trigger.start,
        end: trigger.start + candidate.insertedText.length,
      },
      metadata: candidate.metadata,
    },
  };
}

export function filterStaleMessageEntities(
  text: string,
  entities: ChannelMessageEntity[],
): ChannelMessageEntity[] {
  return entities.filter((entity) => text.includes(entity.insertedText));
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
