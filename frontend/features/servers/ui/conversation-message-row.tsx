"use client";

import * as React from "react";
import {
  Bookmark,
  CalendarDays,
  ChevronDown,
  ChevronUp,
  Copy,
  MessageSquare,
  Shield,
  SmilePlus,
  SquareCheckBig,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { FileCard } from "@/components/shared/file-card";
import type { InputFile } from "@/features/chat/types";
import {
  getUserAvatarUrl,
  getUserDisplayName,
} from "@/features/servers/lib/server-conversation-view";
import { getServerMessageText } from "@/features/servers/lib/server-message-text";
import { getAgentRuntimeStatus } from "@/features/servers/lib/agent-runtime-status";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import type {
  ServerAgentItem,
  ServerChannelMemberItem,
  ServerConversationMessage,
  ServerConversationMessageReactionActor,
  ServerExecutionMessageContent,
  ServerUserPublicProfile,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  getChannelEventContent,
  getChannelEventLabelKey,
  getMessageSessionId,
  isExecutionDrilldownMessage,
} from "../lib/server-conversation-messages";
import { ServerMessageContent } from "./server-message-content";
import { ServerAgentAvatar } from "./server-agent-avatar";
import { MessageReactionPicker } from "./message-reaction-picker";

const MESSAGE_COLLAPSE_LINES = 8;
const MAX_REACTION_ACTOR_NAME_LENGTH = 18;

type MessageRowProps = {
  message: ServerConversationMessage;
  agents?: ServerAgentItem[];
  members?: ServerChannelMemberItem[];
  presets?: Preset[];
  channelLabel?: string;
  isSaved?: boolean;
  compact?: boolean;
  defaultExpanded?: boolean;
  onOpenThread: () => void;
  onOpenExecution?: ((sessionId: string) => void) | undefined;
  onOpenAgentProfile?: ((agentId: string) => void) | undefined;
  onToggleSaved: () => void;
  onToggleReaction?: (emoji: string) => void;
};

export function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatRelativeDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (diffDays <= 0) {
    return "Today";
  }
  if (diffDays === 1) {
    return "Yesterday";
  }
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    date,
  );
}

export function getInitials(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "?";
  }
  return trimmed
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join("");
}

export function getMessageText(message: ServerConversationMessage): string {
  return getServerMessageText(message);
}

function formatSummaryDate(value: string, locale?: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}

function isInputFile(value: unknown): value is InputFile {
  return (
    Boolean(value) &&
    typeof value === "object" &&
    typeof (value as { name?: unknown }).name === "string" &&
    typeof (value as { source?: unknown }).source === "string"
  );
}

function getMessageAttachments(
  message: ServerConversationMessage,
): InputFile[] {
  const attachments = message.content.attachments;
  if (!Array.isArray(attachments)) {
    return [];
  }
  return attachments.filter(isInputFile);
}

export function getMessageAuthor(message: ServerConversationMessage): string {
  if (message.messageType === "event") {
    const event = getChannelEventContent(message);
    return event?.actorLabel?.trim() || "System";
  }
  if (message.messageType === "system") {
    const actor = message.content.actor_label;
    if (typeof actor === "string" && actor.trim()) {
      return actor.trim();
    }
    return "System";
  }
  if (message.messageType === "task") {
    const creator = message.content.creator_user_id;
    if (typeof creator === "string" && creator.trim()) {
      return creator.trim();
    }
    return "Task";
  }
  return getUserDisplayName(message.authorUser, message.authorUserId);
}

function getEventActorLabel(value: unknown): string {
  if (!value || typeof value !== "object") {
    return "";
  }
  const label = (value as { label?: unknown }).label;
  return typeof label === "string" ? label.trim() : "";
}

type HumanSummaryOverride = {
  label: string;
  userId: string | null;
  user: ServerUserPublicProfile | null;
};

function normalizeSummaryLookup(value: string | null | undefined): string {
  return value?.trim().toLowerCase() ?? "";
}

function findChannelEventAgent(
  agents: ServerAgentItem[],
  identityId: string | null | undefined,
  handle: string | null | undefined,
  label: string,
): ServerAgentItem | null {
  const normalizedHandle = normalizeSummaryLookup(handle);
  const normalizedLabel = normalizeSummaryLookup(label);
  return (
    agents.find((agent) => {
      return (
        (identityId && agent.id === identityId) ||
        (normalizedHandle &&
          normalizeSummaryLookup(agent.handle) === normalizedHandle) ||
        (normalizedLabel &&
          normalizeSummaryLookup(agent.displayName) === normalizedLabel)
      );
    }) ?? null
  );
}

function findChannelEventMember(
  members: ServerChannelMemberItem[],
  userId: string | null | undefined,
  label: string,
): ServerChannelMemberItem | null {
  const normalizedLabel = normalizeSummaryLookup(label);
  return (
    members.find((member) => {
      const memberLabel = getUserDisplayName(member.user, member.userId);
      return (
        (userId && member.userId === userId) ||
        (normalizedLabel &&
          (normalizeSummaryLookup(member.userId) === normalizedLabel ||
            normalizeSummaryLookup(memberLabel) === normalizedLabel))
      );
    }) ?? null
  );
}

function ChannelEventRow({
  message,
  agents = [],
  members = [],
  presets = [],
  compact,
}: Pick<
  MessageRowProps,
  "message" | "agents" | "members" | "presets" | "compact"
>) {
  const { t } = useT("translation");
  const event = getChannelEventContent(message);
  if (!event) {
    return null;
  }

  const actor = event.actorLabel?.trim() || t("conversationView.events.actor");
  const target = event.targetLabel?.trim() || actor;
  const taskTitle =
    event.taskTitle?.trim() ||
    event.title?.trim() ||
    t("conversationView.events.task");
  const taskNumber =
    event.taskNumber === null || event.taskNumber === undefined
      ? ""
      : String(event.taskNumber);
  const assignee = getEventActorLabel(event.assignee);
  const fromAssignee = getEventActorLabel(event.fromAssignee);
  const toAssignee = getEventActorLabel(event.toAssignee);
  const task = taskNumber ? `#${taskNumber}: ${taskTitle}` : taskTitle;
  const labelKey =
    event.eventType === "task.created" && assignee
      ? "conversationView.events.taskCreatedAssigned"
      : getChannelEventLabelKey(event.eventType);
  const label = t(labelKey, {
    actor,
    target,
    task,
    taskTitle,
    taskNumber,
    assignee,
    fromAssignee,
    toAssignee,
    comment: event.commentText ?? "",
    fromStatus: event.fromStatus ?? "",
    toStatus: event.toStatus ?? event.status ?? "",
  });
  const fallbackName =
    event.eventType === "channel.agent_joined" ? target : actor;
  const summaryUsesTarget = event.eventType === "channel.agent_joined";
  const summaryAgent = findChannelEventAgent(
    agents,
    summaryUsesTarget
      ? event.targetAgentIdentityId
      : event.actorAgentIdentityId,
    summaryUsesTarget ? event.targetAgentHandle : event.actorAgentHandle,
    fallbackName,
  );
  const summaryMember = summaryAgent
    ? null
    : findChannelEventMember(
        members,
        summaryUsesTarget ? event.targetUserId : event.actorUserId,
        fallbackName,
      );
  const summaryUserId =
    summaryMember?.userId ??
    (summaryUsesTarget ? event.targetUserId : event.actorUserId) ??
    null;
  const summaryHuman =
    summaryAgent || (!summaryMember && !summaryUserId)
      ? null
      : {
          label: summaryMember
            ? getUserDisplayName(summaryMember.user, summaryMember.userId)
            : fallbackName,
          userId: summaryUserId,
          user: summaryMember?.user ?? null,
        };
  const isJoinEvent =
    event.eventType === "channel.member_joined" ||
    event.eventType === "channel.agent_joined";

  return (
    <article
      className={cn(
        "flex items-center gap-2 border-b border-border px-6 py-3 text-sm text-muted-foreground last:border-b-0",
        compact && "py-2.5",
      )}
    >
      <span className="flex size-7 shrink-0 items-center justify-center text-base">
        {isJoinEvent ? (
          <span aria-hidden="true">👋</span>
        ) : (
          <SquareCheckBig className="size-4" aria-hidden="true" />
        )}
      </span>
      <div className="min-w-0 flex-1 truncate leading-6">
        <span className="truncate">
          {summaryAgent || summaryHuman ? (
            <AvatarSummaryTrigger
              message={message}
              matchingAgent={summaryAgent}
              member={summaryMember}
              presets={presets}
              humanSummary={summaryHuman}
            >
              <span className="font-medium text-muted-foreground underline decoration-muted-foreground/50 underline-offset-4">
                {fallbackName}
              </span>
            </AvatarSummaryTrigger>
          ) : (
            <span className="font-medium text-muted-foreground underline decoration-muted-foreground/50 underline-offset-4">
              {fallbackName}
            </span>
          )}
          {label.startsWith(fallbackName)
            ? label.slice(fallbackName.length)
            : ` ${label}`}
        </span>
        <span className="whitespace-nowrap">
          {" "}
          · {formatRelativeDate(message.createdAt)}{" "}
          {formatTime(message.createdAt)}
        </span>
      </div>
    </article>
  );
}

function getReactionActorName(
  actor: ServerConversationMessageReactionActor,
): string {
  if (actor.actorType === "user") {
    return getUserDisplayName(actor.user, actor.userId);
  }
  return (
    actor.agentLabel?.trim() ||
    actor.agentHandle?.trim() ||
    actor.agentIdentityId?.trim() ||
    "Agent"
  );
}

function truncateReactionActorName(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length <= MAX_REACTION_ACTOR_NAME_LENGTH) {
    return trimmed;
  }
  return `${trimmed.slice(0, MAX_REACTION_ACTOR_NAME_LENGTH - 3)}...`;
}

function AvatarSummaryCard({
  message,
  matchingAgent,
  member,
  presets,
  humanSummary,
}: {
  message: ServerConversationMessage;
  matchingAgent: ServerAgentItem | null;
  member: ServerChannelMemberItem | null;
  presets: Preset[];
  humanSummary?: HumanSummaryOverride | null;
}) {
  const { t, i18n } = useT("translation");

  if (matchingAgent) {
    const runtimeStatus = getAgentRuntimeStatus(matchingAgent);
    const description = matchingAgent.description?.trim();
    return (
      <div className="w-60 overflow-hidden text-foreground">
        <div className="flex items-center gap-3 px-3 py-2.5">
          <ServerAgentAvatar
            agent={matchingAgent}
            presets={presets}
            className="size-11 shrink-0"
            fallbackClassName="text-sm"
          />
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-1.5">
              <p className="truncate text-sm font-semibold">
                {matchingAgent.displayName}
              </p>
              <span className="size-1.5 shrink-0 rounded-full bg-muted-foreground" />
              <span className="shrink-0 text-[11px] leading-none text-muted-foreground">
                {t(runtimeStatus.labelKey)}
              </span>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              @{matchingAgent.handle}
            </p>
          </div>
        </div>
        <div className="border-t border-border/80 px-3 py-2">
          <p className="line-clamp-2 text-xs leading-5 text-muted-foreground">
            {description ||
              t("conversationView.colleagues.agentEmptyDescription")}
          </p>
        </div>
      </div>
    );
  }

  const author = humanSummary?.label ?? getMessageAuthor(message);
  const avatarUrl = getUserAvatarUrl(humanSummary?.user ?? message.authorUser);
  const authorUserId = humanSummary?.userId ?? message.authorUserId;
  const secondaryLabel =
    authorUserId?.trim() && authorUserId !== author ? authorUserId : null;
  const roleLabel = member?.role ?? null;
  const joinedLabel = member?.joinedAt
    ? formatSummaryDate(member.joinedAt, i18n.resolvedLanguage ?? i18n.language)
    : null;

  return (
    <div className="w-60 overflow-hidden text-foreground">
      <div className="flex items-center gap-3 px-3 py-2.5">
        <Avatar className="size-11 shrink-0 rounded-md border border-border">
          {avatarUrl ? <AvatarImage src={avatarUrl} alt={author} /> : null}
          <AvatarFallback className="rounded-md bg-muted text-sm font-semibold text-foreground">
            {getInitials(author)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{author}</p>
          {secondaryLabel ? (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {secondaryLabel}
            </p>
          ) : null}
        </div>
      </div>
      <div className="border-t border-border/80 px-3 py-2 text-xs leading-5 text-muted-foreground">
        {roleLabel || joinedLabel ? (
          <div className="flex min-w-0 items-center gap-3">
            {roleLabel ? (
              <p className="flex min-w-0 items-center gap-1.5">
                <Shield className="size-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate">{roleLabel}</span>
              </p>
            ) : null}
            {joinedLabel ? (
              <p className="ml-auto flex min-w-0 shrink-0 items-center gap-1.5 text-right">
                <CalendarDays
                  className="size-3.5 shrink-0"
                  aria-hidden="true"
                />
                <span className="truncate">{joinedLabel}</span>
              </p>
            ) : null}
          </div>
        ) : (
          <p className="truncate">
            {t("conversationView.colleagues.emptyValue")}
          </p>
        )}
      </div>
    </div>
  );
}

function AvatarSummaryTrigger({
  children,
  message,
  matchingAgent,
  member,
  presets,
  humanSummary,
}: {
  children: React.ReactNode;
  message: ServerConversationMessage;
  matchingAgent: ServerAgentItem | null;
  member: ServerChannelMemberItem | null;
  presets: Preset[];
  humanSummary?: HumanSummaryOverride | null;
}) {
  return (
    <HoverCard openDelay={120} closeDelay={80}>
      <HoverCardTrigger asChild>{children}</HoverCardTrigger>
      <HoverCardContent
        side="top"
        align="center"
        sideOffset={10}
        className="w-auto overflow-hidden rounded-md border border-border/60 bg-background p-0 shadow-[var(--shadow-md)]"
      >
        <AvatarSummaryCard
          message={message}
          matchingAgent={matchingAgent}
          member={member}
          presets={presets}
          humanSummary={humanSummary}
        />
      </HoverCardContent>
    </HoverCard>
  );
}

export function isExecutionMessage(
  message: ServerConversationMessage,
): message is ServerConversationMessage & {
  content: ServerExecutionMessageContent;
} {
  return (
    message.messageType === "system" &&
    message.content.source === "agent_execution"
  );
}

function getExecutionStatusTone(status: string | null | undefined): string {
  switch ((status || "").trim().toLowerCase()) {
    case "completed":
      return "bg-emerald-500";
    case "canceled":
    case "cancelled":
      return "bg-muted-foreground";
    case "failed":
      return "bg-destructive";
    case "canceling":
      return "bg-orange-500";
    case "running":
      return "bg-amber-500";
    default:
      return "bg-muted-foreground";
  }
}

function getExecutionStatusLabelKey(status: string | null | undefined): string {
  switch ((status || "").trim().toLowerCase()) {
    case "completed":
      return "conversationView.execution.status.completed";
    case "canceled":
    case "cancelled":
      return "conversationView.execution.status.canceled";
    case "failed":
      return "conversationView.execution.status.failed";
    case "canceling":
      return "conversationView.execution.status.canceling";
    case "running":
      return "conversationView.execution.status.running";
    default:
      return "conversationView.execution.status.queued";
  }
}

function StandardMessageRow({
  message,
  agents = [],
  members = [],
  presets = [],
  channelLabel,
  isSaved = false,
  compact = false,
  defaultExpanded = false,
  onOpenThread,
  onOpenExecution,
  onOpenAgentProfile,
  onToggleSaved,
  onToggleReaction,
}: MessageRowProps) {
  const { t } = useT("translation");
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded);
  const [shouldCollapse, setShouldCollapse] = React.useState(false);
  const [reactionPickerOpen, setReactionPickerOpen] = React.useState(false);
  const agentMessageRef = React.useRef<HTMLDivElement>(null);
  const author = getMessageAuthor(message);
  const attachments = getMessageAttachments(message);
  const contentText =
    typeof message.content.text === "string" ? message.content.text.trim() : "";
  const text = attachments.length > 0 ? contentText : getMessageText(message);
  const executionMessage = isExecutionMessage(message) ? message : null;
  const drilldownSessionId = getMessageSessionId(message);
  const canOpenExecutionFromAvatar =
    Boolean(onOpenExecution) && isExecutionDrilldownMessage(message);
  const avatarUrl = getUserAvatarUrl(message.authorUser);
  const matchingMember =
    message.authorUserId != null
      ? (members.find((member) => member.userId === message.authorUserId) ??
        null)
      : null;
  const matchingAgent =
    message.messageType === "system"
      ? (message.authorAgent ??
        agents.find((agent) => {
          const contentHandle =
            typeof message.content.agent_handle === "string"
              ? message.content.agent_handle.trim().toLowerCase()
              : "";
          const contentActor =
            typeof message.content.actor_label === "string"
              ? message.content.actor_label.trim().toLowerCase()
              : "";
          return (
            (contentHandle &&
              agent.handle.trim().toLowerCase() === contentHandle) ||
            (contentActor &&
              agent.displayName.trim().toLowerCase() === contentActor)
          );
        }) ??
        null)
      : null;
  const executionSessionId =
    executionMessage && typeof executionMessage.content.session_id === "string"
      ? executionMessage.content.session_id
      : null;
  const canCollapseMessage =
    !executionMessage && Boolean(text) && message.messageType !== "task";

  const handleCopyMessage = React.useCallback(async () => {
    if (!text) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t("chat.copyMessage"));
    } catch (error) {
      console.error("[ConversationMessageRow] failed to copy message", error);
      toast.error(t("chat.copyFailed"));
    }
  }, [t, text]);

  React.useEffect(() => {
    setIsExpanded(defaultExpanded);
    setReactionPickerOpen(false);
  }, [defaultExpanded, message.id, text]);

  React.useEffect(() => {
    if (!canCollapseMessage) {
      setShouldCollapse(false);
      return;
    }

    const element = agentMessageRef.current;
    if (!element) return;

    const checkOverflow = () => {
      const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
      const thresholdHeight = lineHeight * MESSAGE_COLLAPSE_LINES;
      setShouldCollapse(element.scrollHeight > thresholdHeight + 1);
    };

    checkOverflow();

    const observer = new ResizeObserver(checkOverflow);
    observer.observe(element);

    return () => observer.disconnect();
  }, [canCollapseMessage, text]);

  return (
    <article
      className={cn(
        "group flex gap-4 border-b border-border px-6 py-5 last:border-b-0",
        compact && "py-4",
      )}
    >
      {matchingAgent ? (
        <AvatarSummaryTrigger
          message={message}
          matchingAgent={matchingAgent}
          member={null}
          presets={presets}
        >
          <button
            type="button"
            onClick={() => {
              if (
                canOpenExecutionFromAvatar &&
                drilldownSessionId &&
                onOpenExecution
              ) {
                onOpenExecution(drilldownSessionId);
                return;
              }
              if (matchingAgent && onOpenAgentProfile) {
                onOpenAgentProfile(matchingAgent.id);
              }
            }}
            className={cn(
              "shrink-0 self-start",
              canOpenExecutionFromAvatar || onOpenAgentProfile
                ? "cursor-pointer"
                : "cursor-default",
            )}
            aria-label={author}
          >
            <ServerAgentAvatar
              agent={matchingAgent}
              presets={presets}
              className="size-11 shrink-0"
              fallbackClassName="text-sm"
            />
          </button>
        </AvatarSummaryTrigger>
      ) : (
        <AvatarSummaryTrigger
          message={message}
          matchingAgent={null}
          member={matchingMember}
          presets={presets}
        >
          <div className="shrink-0 self-start">
            <Avatar className="size-11 rounded-md border border-border">
              {avatarUrl ? <AvatarImage src={avatarUrl} alt={author} /> : null}
              <AvatarFallback className="rounded-md bg-muted text-sm font-semibold text-foreground">
                {getInitials(author)}
              </AvatarFallback>
            </Avatar>
          </div>
        </AvatarSummaryTrigger>
      )}
      <div className="relative min-w-0 flex-1 space-y-1.5">
        <div className="flex items-start justify-between gap-3 text-sm">
          <div className="min-w-0 flex flex-wrap items-center gap-3">
            <span className="text-sm font-semibold text-foreground">
              {author}
            </span>
            <span className="text-sm text-muted-foreground">
              {formatRelativeDate(message.createdAt)}{" "}
              {formatTime(message.createdAt)}
            </span>
            {channelLabel ? (
              <span className="text-sm text-muted-foreground">
                #{channelLabel}
              </span>
            ) : null}
          </div>
          <div className="absolute right-0 top-0 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
            {onToggleReaction ? (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setReactionPickerOpen((open) => !open)}
                  aria-label={t("conversationView.reactions.add")}
                  title={t("conversationView.reactions.add")}
                  className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
                >
                  <SmilePlus className="size-4" />
                </button>
                <MessageReactionPicker
                  open={reactionPickerOpen}
                  onOpenChange={setReactionPickerOpen}
                  onSelect={onToggleReaction}
                />
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => void handleCopyMessage()}
              aria-label={t("chat.copyMessage")}
              className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            >
              <Copy className="size-4" />
            </button>
            <button
              type="button"
              onClick={onOpenThread}
              aria-label={t("conversationView.reply")}
              className="inline-flex size-8 items-center justify-center gap-1 rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            >
              <MessageSquare className="size-3.5" />
              {message.replyCount > 0 ? (
                <span className="tabular-nums">{message.replyCount}</span>
              ) : null}
            </button>
            <button
              type="button"
              onClick={onToggleSaved}
              aria-label={
                isSaved
                  ? t("conversationView.unsave")
                  : t("conversationView.save")
              }
              className="inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground"
            >
              <Bookmark
                className={isSaved ? "size-3.5 fill-current" : "size-3.5"}
              />
            </button>
          </div>
        </div>
        {executionMessage ? (
          <button
            type="button"
            onClick={() => {
              if (executionSessionId && onOpenExecution) {
                onOpenExecution(executionSessionId);
              }
            }}
            disabled={!executionSessionId || !onOpenExecution}
            className={cn(
              "w-full rounded-md border border-border bg-muted/20 p-4 text-left",
              executionSessionId && onOpenExecution
                ? "transition-colors hover:bg-muted/35"
                : "cursor-default",
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground">
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      getExecutionStatusTone(
                        executionMessage.content.execution_status,
                      ),
                    )}
                  />
                  {t(
                    getExecutionStatusLabelKey(
                      executionMessage.content.execution_status,
                    ),
                  )}
                </span>
                {executionMessage.content.todo_progress &&
                executionMessage.content.todo_progress.total > 0 ? (
                  <span className="text-xs text-muted-foreground">
                    {t("conversationView.execution.todoProgress", {
                      completed:
                        executionMessage.content.todo_progress.completed ?? 0,
                      total: executionMessage.content.todo_progress.total ?? 0,
                    })}
                  </span>
                ) : null}
              </div>
              {executionMessage.content.current_step ? (
                <p className="min-w-0 max-w-[40%] truncate text-right text-sm font-medium text-foreground">
                  {executionMessage.content.current_step}
                </p>
              ) : null}
            </div>
            <div className="mt-2 max-h-[4.5rem] cursor-text select-text overflow-hidden text-sm leading-6 text-muted-foreground">
              <ServerMessageContent
                content={text || t("conversationView.execution.emptySummary")}
                messageContent={message.content}
              />
            </div>
          </button>
        ) : text || attachments.length === 0 ? (
          <div className="group/message min-w-0">
            <div
              ref={agentMessageRef}
              className={cn(
                "relative cursor-text select-text text-base leading-7 text-foreground",
                canCollapseMessage &&
                  shouldCollapse &&
                  !isExpanded &&
                  "max-h-56 overflow-hidden",
              )}
            >
              <ServerMessageContent
                content={text || t("conversationView.emptyMessage")}
                messageContent={message.content}
              />
              {canCollapseMessage && shouldCollapse && !isExpanded ? (
                <div className="pointer-events-none absolute inset-x-0 bottom-0 flex h-10 items-end bg-gradient-to-t from-background via-background/90 to-transparent">
                  <span className="text-sm leading-none text-muted-foreground">
                    ...
                  </span>
                </div>
              ) : null}
            </div>
            {canCollapseMessage && shouldCollapse ? (
              <button
                type="button"
                onClick={() => setIsExpanded((value) => !value)}
                className="mt-2 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="size-4" />
                    {t("chat.collapse")}
                  </>
                ) : (
                  <>
                    <ChevronDown className="size-4" />
                    {t("chat.expand")}
                  </>
                )}
              </button>
            ) : null}
          </div>
        ) : null}
        {attachments.length > 0 ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {attachments.map((file, index) => (
              <FileCard
                key={`${file.source}-${index}`}
                file={file}
                showRemove={false}
                className="w-full max-w-56 bg-background"
              />
            ))}
          </div>
        ) : null}
        {(message.reactions ?? []).length > 0 ? (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {(message.reactions ?? []).map((reaction) => {
              const selected = reaction.reactedByCurrentUser;
              const actorNames = reaction.actors
                .map(getReactionActorName)
                .filter(Boolean);
              const visibleActorNames = actorNames.map(
                truncateReactionActorName,
              );
              const label = selected
                ? t("conversationView.reactions.removeEmoji", {
                    emoji: reaction.emoji,
                  })
                : t("conversationView.reactions.addEmoji", {
                    emoji: reaction.emoji,
                  });
              const title = actorNames.length
                ? `${label} | ${actorNames.join(", ")}`
                : label;
              return (
                <button
                  key={reaction.emoji}
                  type="button"
                  disabled={!onToggleReaction}
                  onClick={() => onToggleReaction?.(reaction.emoji)}
                  aria-label={title}
                  title={title}
                  className={cn(
                    "inline-flex h-7 max-w-full items-center justify-center gap-1 overflow-hidden rounded-md border px-2 text-sm transition-colors",
                    selected
                      ? "border-primary/50 bg-primary/15 text-foreground"
                      : "border-border bg-muted/20 text-muted-foreground hover:bg-muted/45 hover:text-foreground",
                    !onToggleReaction && "cursor-default",
                  )}
                >
                  <span className="shrink-0">{reaction.emoji}</span>
                  <span className="shrink-0 text-xs tabular-nums">
                    {reaction.count}
                  </span>
                  {visibleActorNames.length > 0 ? (
                    <>
                      <span
                        className="shrink-0 text-xs text-muted-foreground"
                        aria-hidden="true"
                      >
                        |
                      </span>
                      <span className="flex min-w-0 max-w-[28rem] shrink items-center overflow-hidden text-xs">
                        {visibleActorNames.map((actorName, index) => (
                          <React.Fragment key={`${reaction.emoji}-${index}`}>
                            {index > 0 ? (
                              <span
                                className="shrink-0 pr-1 text-muted-foreground"
                                aria-hidden="true"
                              >
                                ,
                              </span>
                            ) : null}
                            <span className="max-w-28 shrink truncate text-left">
                              {actorName}
                            </span>
                          </React.Fragment>
                        ))}
                      </span>
                    </>
                  ) : null}
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </article>
  );
}

export function MessageRow(props: MessageRowProps) {
  if (props.message.messageType === "event") {
    return (
      <ChannelEventRow
        message={props.message}
        agents={props.agents}
        members={props.members}
        presets={props.presets}
        compact={props.compact}
      />
    );
  }
  return <StandardMessageRow {...props} />;
}
