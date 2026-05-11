"use client";

import * as React from "react";
import {
  Bookmark,
  ChevronDown,
  ChevronUp,
  Copy,
  MessageSquare,
  SmilePlus,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  getUserAvatarUrl,
  getUserDisplayName,
} from "@/features/servers/lib/server-conversation-view";
import { getServerMessageText } from "@/features/servers/lib/server-message-text";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import type {
  ServerAgentItem,
  ServerConversationMessage,
  ServerConversationMessageReactionActor,
  ServerExecutionMessageContent,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
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
  presets?: Preset[];
  channelLabel?: string;
  isSaved?: boolean;
  compact?: boolean;
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

function ChannelEventRow({
  message,
  agents = [],
  presets = [],
  compact,
}: Pick<MessageRowProps, "message" | "agents" | "presets" | "compact">) {
  const { t } = useT("translation");
  const event = getChannelEventContent(message);
  if (!event) {
    return null;
  }

  const actor = event.actorLabel?.trim() || t("conversationView.events.actor");
  const target = event.targetLabel?.trim() || actor;
  const task = event.title?.trim() || t("conversationView.events.task");
  const label = t(getChannelEventLabelKey(event.eventType), {
    actor,
    target,
    task,
    fromStatus: event.fromStatus ?? "",
    toStatus: event.toStatus ?? event.status ?? "",
  });
  const agentIdentityId =
    event.eventType === "channel.agent_joined"
      ? event.targetAgentIdentityId
      : event.actorAgentIdentityId;
  const agentHandle =
    event.eventType === "channel.agent_joined"
      ? event.targetAgentHandle
      : event.actorAgentHandle;
  const matchingAgent =
    agents.find((agent) => agent.id === agentIdentityId) ??
    agents.find((agent) => agent.handle === agentHandle) ??
    null;
  const fallbackName =
    event.eventType === "channel.agent_joined" ? target : actor;

  return (
    <article
      className={cn(
        "flex gap-3 border-b border-border px-6 py-3 last:border-b-0",
        compact && "py-2.5",
      )}
    >
      {matchingAgent ? (
        <ServerAgentAvatar
          agent={matchingAgent}
          presets={presets}
          className="mt-0.5 size-7 shrink-0"
          fallbackClassName="text-xs"
        />
      ) : (
        <Avatar className="mt-0.5 size-7 shrink-0 rounded-md border border-border">
          <AvatarFallback className="rounded-md bg-muted text-xs font-semibold text-muted-foreground">
            {getInitials(fallbackName)}
          </AvatarFallback>
        </Avatar>
      )}
      <div className="min-w-0 rounded-md bg-muted/20 px-3 py-1.5 text-sm leading-6 text-muted-foreground">
        <span className="break-words">{label}</span>
        <span className="whitespace-nowrap">
          {" "}
          · {formatTime(message.createdAt)}
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
  presets = [],
  channelLabel,
  isSaved = false,
  compact = false,
  onOpenThread,
  onOpenExecution,
  onOpenAgentProfile,
  onToggleSaved,
  onToggleReaction,
}: MessageRowProps) {
  const { t } = useT("translation");
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [shouldCollapse, setShouldCollapse] = React.useState(false);
  const [reactionPickerOpen, setReactionPickerOpen] = React.useState(false);
  const agentMessageRef = React.useRef<HTMLDivElement>(null);
  const author = getMessageAuthor(message);
  const text = getMessageText(message);
  const executionMessage = isExecutionMessage(message) ? message : null;
  const drilldownSessionId = getMessageSessionId(message);
  const canOpenExecutionFromAvatar =
    Boolean(onOpenExecution) && isExecutionDrilldownMessage(message);
  const avatarUrl = getUserAvatarUrl(message.authorUser);
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
    setIsExpanded(false);
    setReactionPickerOpen(false);
  }, [message.id, text]);

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
          disabled={!canOpenExecutionFromAvatar && !onOpenAgentProfile}
          className={cn(
            "shrink-0 self-start",
            canOpenExecutionFromAvatar || onOpenAgentProfile
              ? "cursor-pointer"
              : "cursor-default",
          )}
          aria-label={author}
          title={author}
        >
          <ServerAgentAvatar
            agent={matchingAgent}
            presets={presets}
            className="size-11 shrink-0"
            fallbackClassName="text-sm"
          />
        </button>
      ) : (
        <Avatar className="size-11 shrink-0 self-start rounded-md border border-border">
          {avatarUrl ? <AvatarImage src={avatarUrl} alt={author} /> : null}
          <AvatarFallback className="rounded-md bg-muted text-sm font-semibold text-foreground">
            {getInitials(author)}
          </AvatarFallback>
        </Avatar>
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
              />
            </div>
          </button>
        ) : (
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
        )}
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
        agents={props.agents ?? []}
        presets={props.presets ?? []}
        compact={props.compact}
      />
    );
  }
  return <StandardMessageRow {...props} />;
}
