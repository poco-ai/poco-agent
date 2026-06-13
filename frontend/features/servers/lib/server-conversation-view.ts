import type { InputFile } from "@/features/chat/types";
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

interface ComposerReferenceRange {
  start: number;
  end: number;
}

interface BaseComposerReference {
  id: string;
  insertedText: string;
  displayText: string;
  range?: ComposerReferenceRange;
  metadata?: Record<string, unknown>;
}

export interface ComposerEntityReference extends BaseComposerReference {
  kind: ChannelMessageEntityKind;
  action: ChannelMessageEntityAction;
  targetId: string;
}

export interface ComposerDraftAttachmentReference extends BaseComposerReference {
  kind: "draft_attachment";
  action: "reference";
  file: InputFile;
}

export type ComposerReference =
  | ComposerEntityReference
  | ComposerDraftAttachmentReference;

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
): { text: string; reference: ComposerEntityReference } {
  const insertText = `${candidate.insertedText} `;
  const replaceEnd = trigger.start + trigger.query.length + 1;
  const text = `${draft.slice(0, trigger.start)}${insertText}${draft.slice(replaceEnd)}`;
  return {
    text,
    reference: {
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

function updateReferenceRange(
  text: string,
  reference: ComposerReference,
): ComposerReference | null {
  const insertedText = reference.insertedText.trim();
  if (!insertedText) {
    return null;
  }
  const start = text.indexOf(insertedText);
  if (start === -1) {
    return null;
  }
  return {
    ...reference,
    range: { start, end: start + insertedText.length },
  };
}

export function filterStaleComposerReferences(
  text: string,
  references: ComposerReference[],
): ComposerReference[] {
  return references
    .map((reference) => updateReferenceRange(text, reference))
    .filter((reference): reference is ComposerReference => reference !== null);
}

export function upsertComposerReference(
  references: ComposerReference[],
  nextReference: ComposerReference,
): ComposerReference[] {
  const reservedText = nextReference.insertedText.trim();
  return [
    ...references.filter(
      (reference) => reference.insertedText.trim() !== reservedText,
    ),
    nextReference,
  ];
}

function normalizeInputFileSource(file: InputFile): string {
  return String(file.source || "").trim();
}

function normalizeInputFileDisplayName(file: InputFile): string {
  return (
    String(file.name || "").trim() || normalizeInputFileSource(file) || "file"
  );
}

export function insertUploadedComposerReference(
  draft: string,
  selectionStart: number,
  selectionEnd: number,
  file: InputFile,
): {
  text: string;
  cursor: number;
  reference: ComposerDraftAttachmentReference;
} | null {
  const source = normalizeInputFileSource(file);
  if (!source) return null;

  const start = Math.max(0, Math.min(selectionStart, draft.length));
  const end = Math.max(start, Math.min(selectionEnd, draft.length));
  const before = draft.slice(0, start);
  const after = draft.slice(end);
  const insertedText = `#${normalizeInputFileDisplayName(file)}`;
  const prefix = before && !/\s$/.test(before) ? " " : "";
  const suffix = after.startsWith(" ") ? "" : " ";
  const replacement = `${prefix}${insertedText}${suffix}`;
  const tokenStart = start + prefix.length;
  const tokenEnd = tokenStart + insertedText.length;

  return {
    text: `${before}${replacement}${after}`,
    cursor: start + replacement.length,
    reference: {
      id: `draft-attachment:${source}:${tokenStart}:${tokenEnd}`,
      kind: "draft_attachment",
      action: "reference",
      insertedText,
      displayText: normalizeInputFileDisplayName(file),
      range: { start: tokenStart, end: tokenEnd },
      file,
      metadata: {
        size: file.size ?? null,
        contentType: file.content_type ?? null,
        path: file.path ?? null,
      },
    },
  };
}

export function getComposerDraftAttachments(
  references: ComposerReference[],
): InputFile[] {
  const seenSources = new Set<string>();
  const attachments: InputFile[] = [];
  for (const reference of references) {
    if (reference.kind !== "draft_attachment") continue;
    const source = normalizeInputFileSource(reference.file);
    if (!source || seenSources.has(source)) continue;
    attachments.push(reference.file);
    seenSources.add(source);
  }
  return attachments;
}

export function getComposerDraftAttachmentReferences(
  references: ComposerReference[],
): ComposerDraftAttachmentReference[] {
  return references.filter(
    (reference): reference is ComposerDraftAttachmentReference =>
      reference.kind === "draft_attachment",
  );
}

export function removeComposerReferenceText(
  text: string,
  reference: ComposerReference,
): { text: string; cursor: number } {
  const insertedText = reference.insertedText.trim();
  if (!insertedText) {
    return { text, cursor: text.length };
  }
  const rangeStart = reference.range?.start ?? text.indexOf(insertedText);
  const rangeEnd =
    reference.range?.end ??
    (rangeStart >= 0 ? rangeStart + insertedText.length : -1);
  if (rangeStart < 0 || rangeEnd < 0 || rangeStart > text.length) {
    return { text, cursor: text.length };
  }

  const before = text.slice(0, rangeStart);
  const after = text.slice(rangeEnd);
  const nextText = `${before}${after}`.replace(/ {2,}/g, " ");
  return {
    text: nextText,
    cursor: Math.min(rangeStart, nextText.length),
  };
}

export function serializeComposerReferencesForSend(
  text: string,
  references: ComposerReference[],
): {
  activeReferences: ComposerReference[];
  entities: ChannelMessageEntity[];
  attachments: InputFile[];
} {
  const activeReferences = filterStaleComposerReferences(text, references);
  const attachments = getComposerDraftAttachments(activeReferences);
  const reservedAttachmentTokens = new Set(
    activeReferences
      .filter(
        (reference): reference is ComposerDraftAttachmentReference =>
          reference.kind === "draft_attachment",
      )
      .map((reference) => reference.insertedText.trim())
      .filter(Boolean),
  );
  const entities = activeReferences
    .filter(
      (reference): reference is ComposerEntityReference =>
        reference.kind !== "draft_attachment",
    )
    .filter(
      (reference) =>
        !(
          reference.kind === "artifact" &&
          reservedAttachmentTokens.has(reference.insertedText.trim())
        ),
    )
    .map<ChannelMessageEntity>((reference) => ({
      id: reference.id,
      kind: reference.kind,
      action: reference.action,
      targetId: reference.targetId,
      displayText: reference.displayText,
      insertedText: reference.insertedText,
      range: reference.range,
      metadata: reference.metadata,
    }));

  return {
    activeReferences,
    entities,
    attachments,
  };
}

export function filterStaleMessageEntities(
  text: string,
  entities: ChannelMessageEntity[],
): ChannelMessageEntity[] {
  return entities.filter((entity) => text.includes(entity.insertedText));
}

export function filterMessageEntitiesForSend(
  text: string,
  entities: ChannelMessageEntity[],
  attachmentReferences: ComposerReference[] = [],
): ChannelMessageEntity[] {
  const activeEntities = filterStaleMessageEntities(text, entities);
  const reservedAttachmentTokens = new Set(
    attachmentReferences
      .filter(
        (reference): reference is ComposerDraftAttachmentReference =>
          reference.kind === "draft_attachment",
      )
      .map((reference) => reference.insertedText.trim())
      .filter(Boolean),
  );
  if (reservedAttachmentTokens.size === 0) {
    return activeEntities;
  }

  return activeEntities.filter(
    (entity) =>
      !(
        entity.kind === "artifact" &&
        reservedAttachmentTokens.has(entity.insertedText.trim())
      ),
  );
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
