"use client";

import React from "react";
import {
  ArrowLeft,
  Bot,
  Files,
  Info,
  Loader2,
  MessageSquare,
  Pause,
  SquareCheckBig,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { ExecutionContainer } from "@/features/chat";
import { cancelCurrentRunAction } from "@/features/chat/actions/session-actions";
import { useExecutionSession } from "@/features/chat/hooks/use-execution-session";
import type {
  ChannelTask,
  ChannelTaskActivityMessage,
} from "@/features/channel-tasks/model/types";
import { channelTasksApi } from "@/features/channel-tasks/api/channel-tasks-api";
import { TaskHistoryProvider } from "@/features/projects/contexts/task-history-context";
import type {
  ChannelMessageEntity,
  ServerAgentItem,
  ServerChannelMemberItem,
  ServerConversationMessage,
} from "@/features/servers/model/types";
import { serversApi } from "@/features/servers";
import {
  buildAgentMentionCandidate,
  buildArtifactComposerCandidate,
  buildHumanMentionCandidates,
  buildParticipantComposerCandidate,
  buildTaskComposerCandidate,
  filterStaleMessageEntities,
  getComposerCandidateSearchText,
  getComposerTrigger,
  insertComposerCandidate,
  type ComposerCandidate,
} from "@/features/servers/lib/server-conversation-view";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { SharedArtifactsDrawer } from "@/features/servers/ui/shared-artifacts-drawer";

import { MessageRow } from "./conversation-message-row";
import {
  getAgentRuntimeDotClassName,
  getAgentRuntimeStatus,
} from "../lib/agent-runtime-status";
import { ServerAgentAvatar } from "./server-agent-avatar";

const overlayDrawerClassName =
  "absolute inset-y-0 right-0 z-30 flex w-full flex-col border-l border-border bg-card md:left-[17rem] md:w-auto lg:left-[18rem] xl:static xl:h-full xl:w-full xl:min-w-0 xl:shrink-0";

const drawerHeaderClassName =
  "flex w-full max-w-full flex-wrap items-center justify-between gap-3 overflow-hidden border-b border-border px-4 py-4 sm:px-6 sm:py-5";

const drawerHeaderActionsClassName =
  "ml-auto flex min-w-0 max-w-full flex-wrap items-center justify-end gap-2";

function toConversationMessage(
  message: ChannelTaskActivityMessage,
): ServerConversationMessage {
  return {
    id: message.messageId,
    channelId: message.channelId,
    authorUserId: message.authorUserId,
    messageType: message.messageType,
    content: message.content,
    textPreview: message.textPreview,
    threadRootMessageId: message.threadRootMessageId,
    replyCount: 0,
    reactions: [],
    createdAt: message.createdAt,
    updatedAt: message.updatedAt,
  };
}

export function ThreadDrawer({
  thread,
  serverId,
  channelId,
  agents,
  presets,
  members,
  currentUserId,
  draft,
  draftEntities,
  suggestedMentionHandle,
  asTask,
  onDraftChange,
  onDraftEntitiesChange,
  onAsTaskChange,
  onSend,
  onClose,
  onOpenExecution,
  onToggleReaction,
  isSending,
}: {
  thread: ServerConversationMessage[];
  serverId: string | null;
  channelId: string;
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerChannelMemberItem[];
  currentUserId?: string | null;
  draft: string;
  draftEntities: ChannelMessageEntity[];
  suggestedMentionHandle?: string | null;
  asTask: boolean;
  onDraftChange: (value: string) => void;
  onDraftEntitiesChange: (value: ChannelMessageEntity[]) => void;
  onAsTaskChange: (value: boolean) => void;
  onSend: () => void;
  onClose: () => void;
  onOpenExecution?: (sessionId: string) => void;
  onToggleReaction?: (
    message: ServerConversationMessage,
    emoji: string,
  ) => void;
  isSending: boolean;
}) {
  const { t } = useT("translation");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const isComposingRef = React.useRef(false);

  const composerTrigger = React.useMemo(() => getComposerTrigger(draft), [draft]);
  const [contextCandidates, setContextCandidates] = React.useState<
    ComposerCandidate[]
  >([]);
  const participantCandidates = React.useMemo<ComposerCandidate[]>(() => {
    const humans = buildHumanMentionCandidates(members, currentUserId);
    const agentCandidates = agents.map(buildAgentMentionCandidate);
    return [...agentCandidates, ...humans]
      .map(buildParticipantComposerCandidate)
      .filter((candidate) =>
        composerTrigger?.prefix === "@"
          ? getComposerCandidateSearchText(candidate).includes(
              composerTrigger.query,
            )
          : true,
      );
  }, [agents, composerTrigger, currentUserId, members]);

  React.useEffect(() => {
    if (!serverId || composerTrigger?.prefix !== "#") {
      setContextCandidates([]);
      return;
    }
    let cancelled = false;
    const timeoutId = window.setTimeout(() => {
      void Promise.all([
        serversApi.listChannelArtifactCandidates(serverId, channelId, {
          q: composerTrigger.query,
          limit: 6,
        }),
        channelTasksApi.listTaskCandidates(serverId, channelId, {
          q: composerTrigger.query,
          limit: 6,
        }),
      ])
        .then(([artifacts, taskCandidates]) => {
          if (cancelled) return;
          setContextCandidates(
            [
              ...artifacts.map(buildArtifactComposerCandidate),
              ...taskCandidates.map(buildTaskComposerCandidate),
            ]
              .filter((candidate) =>
                getComposerCandidateSearchText(candidate).includes(
                  composerTrigger.query,
                ),
              )
              .slice(0, 8),
          );
        })
        .catch((error) => {
          if (!cancelled) {
            console.error("[ThreadDrawer] load context candidates failed", error);
            setContextCandidates([]);
          }
        });
    }, 150);
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [channelId, composerTrigger, serverId]);

  const composerCandidates =
    composerTrigger?.prefix === "@"
      ? participantCandidates.slice(0, 8)
      : contextCandidates;

  const composerActive =
    composerTrigger !== null && composerCandidates.length > 0;
  const [mentionIndex, setMentionIndex] = React.useState(0);
  React.useEffect(() => {
    setMentionIndex(0);
  }, [composerCandidates]);

  const insertCandidate = (candidate: ComposerCandidate) => {
    if (!composerTrigger) return;
    const inserted = insertComposerCandidate(draft, composerTrigger, candidate);
    onDraftChange(inserted.text);
    onDraftEntitiesChange(
      filterStaleMessageEntities(inserted.text, [
        ...draftEntities,
        inserted.entity,
      ]),
    );
    textareaRef.current?.focus();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (composerActive && event.key === "ArrowDown") {
      event.preventDefault();
      setMentionIndex((i) => (i + 1) % composerCandidates.length);
      return;
    }
    if (composerActive && event.key === "ArrowUp") {
      event.preventDefault();
      setMentionIndex(
        (i) => (i - 1 + composerCandidates.length) % composerCandidates.length,
      );
      return;
    }
    if (composerActive && event.key === "Enter") {
      event.preventDefault();
      insertCandidate(composerCandidates[mentionIndex]);
      return;
    }
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing &&
      !isComposingRef.current
    ) {
      event.preventDefault();
      if (!isSending && draft.trim()) {
        onSend();
      }
    }
  };

  return (
    <aside className={overlayDrawerClassName}>
      <div className={drawerHeaderClassName}>
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-xl font-semibold text-foreground">
            {t("conversationView.threadTitle")}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {thread.map((message, index) => (
          <MessageRow
            key={message.id}
            message={message}
            agents={agents}
            members={members}
            presets={presets}
            defaultExpanded={index === thread.length - 1}
            onOpenThread={() => undefined}
            onOpenExecution={onOpenExecution}
            onToggleSaved={() => undefined}
            onToggleReaction={(emoji) => onToggleReaction?.(message, emoji)}
          />
        ))}
      </div>
      <div className="border-t border-border px-6 py-5">
        {suggestedMentionHandle ? (
          <div className="mb-3 flex items-center gap-2 rounded-md border border-border bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
            <Info className="size-4 shrink-0 text-muted-foreground" />
            <span>
              {t("conversationView.threadMentionHint")}{" "}
              <span className="font-medium text-foreground">
                @{suggestedMentionHandle}
              </span>
            </span>
          </div>
        ) : null}
        <div className="relative">
          {composerActive ? (
            <div className="absolute bottom-full left-0 z-20 mb-2 w-full max-w-md rounded-md border border-border bg-popover p-2 shadow-[var(--shadow-lg)]">
              <div className="px-2 pb-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                {t("conversationView.mentionCandidates")}
              </div>
              <div className="space-y-1">
                {composerCandidates.map((candidate, index) => {
                  const CandidateIcon =
                    candidate.kind === "agent"
                      ? Bot
                      : candidate.kind === "user"
                        ? UserRound
                        : candidate.kind === "task"
                          ? SquareCheckBig
                          : Files;
                  return (
                    <button
                      key={`${candidate.kind}-${candidate.id}`}
                      type="button"
                      onClick={() => insertCandidate(candidate)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors",
                        index === mentionIndex
                          ? "bg-primary/15"
                          : "hover:bg-muted/30",
                      )}
                    >
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                        <CandidateIcon className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-foreground">
                          {candidate.label}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {candidate.metaLabel || candidate.insertedText} /{" "}
                          {t(`conversationView.mentionKinds.${candidate.kind}`)}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          <Textarea
            ref={textareaRef}
            value={draft}
            onChange={(event) => {
              const nextDraft = event.target.value;
              onDraftChange(nextDraft);
              onDraftEntitiesChange(
                filterStaleMessageEntities(nextDraft, draftEntities),
              );
            }}
            onKeyDown={handleKeyDown}
            onCompositionStart={() => {
              isComposingRef.current = true;
            }}
            onCompositionEnd={() => {
              window.requestAnimationFrame(() => {
                isComposingRef.current = false;
              });
            }}
            rows={6}
            placeholder={t("conversationView.threadPlaceholder")}
            className="rounded-md border-border bg-background text-sm shadow-none"
          />
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-3 text-base text-foreground">
            <input
              type="checkbox"
              checked={asTask}
              onChange={(event) => onAsTaskChange(event.target.checked)}
              className="size-5 rounded-none border-foreground"
            />
            {t("conversationView.asTask")}
          </label>
          <Button
            type="button"
            size="sm"
            onClick={onSend}
            disabled={isSending || !draft.trim()}
          >
            {t("conversationView.send")}
          </Button>
        </div>
      </div>
    </aside>
  );
}

export function AgentDrawer({
  agents,
  presets,
  selectedAgentId,
  canInspectPersistentFiles,
  onSelectAgent,
  onClose,
  onOpenDm,
}: {
  agents: ServerAgentItem[];
  presets: Preset[];
  selectedAgentId: string | null | undefined;
  canInspectPersistentFiles?: boolean;
  onSelectAgent: (id: string) => void;
  onClose: () => void;
  onOpenDm: (agentId: string) => void;
}) {
  const { t } = useT("translation");
  const selectedAgent =
    agents.find((agent) => agent.id === selectedAgentId) ?? agents[0] ?? null;
  const selectedRuntimeStatus = selectedAgent
    ? getAgentRuntimeStatus(selectedAgent)
    : null;
  return (
    <aside className={overlayDrawerClassName}>
      <div className={drawerHeaderClassName}>
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-xl font-semibold text-foreground">
            {t("servers.agents.title")}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="space-y-3">
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => onSelectAgent(agent.id)}
              className={cn(
                "w-full rounded-md border px-4 py-4 text-left transition-colors",
                agent.id === selectedAgent?.id
                  ? "border-primary/40 bg-primary/10"
                  : "border-border bg-card hover:bg-muted/20",
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-base font-semibold text-foreground">
                  {agent.displayName}
                </p>
                {(() => {
                  const runtimeStatus = getAgentRuntimeStatus(agent);
                  return (
                    <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          getAgentRuntimeDotClassName(runtimeStatus.tone),
                        )}
                      />
                      {t(runtimeStatus.labelKey)}
                    </span>
                  );
                })()}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                @{agent.handle}
              </p>
            </button>
          ))}
        </div>
        {selectedAgent ? (
          <div className="mt-6 space-y-4 border-t border-border pt-6">
            <div className="flex items-start gap-4">
              <ServerAgentAvatar
                agent={selectedAgent}
                presets={presets}
                className="size-14 shrink-0"
                fallbackClassName="text-lg"
              />
              <div className="min-w-0 flex-1 space-y-2">
                <div className="flex items-center gap-3">
                  <p className="text-lg font-semibold text-foreground">
                    {selectedAgent.displayName}
                  </p>
                  {selectedRuntimeStatus ? (
                    <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground">
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          getAgentRuntimeDotClassName(
                            selectedRuntimeStatus.tone,
                          ),
                        )}
                      />
                      {t(selectedRuntimeStatus.labelKey)}
                    </span>
                  ) : null}
                </div>
                <p className="text-sm text-muted-foreground">
                  @{selectedAgent.handle}
                </p>
                <p className="text-sm text-muted-foreground">
                  {selectedAgent.description ||
                    t("conversationView.colleagues.agentEmptyDescription")}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedRuntimeStatus ? (
                <Badge variant="secondary">
                  {t(selectedRuntimeStatus.labelKey)}
                </Badge>
              ) : null}
              <Badge variant="outline">
                {selectedRuntimeStatus?.rawRuntimeStatus ??
                  t("servers.agents.unknown")}
              </Badge>
              <Badge variant="outline">@{selectedAgent.handle}</Badge>
            </div>
            <div className="space-y-3 text-sm">
              <div className="rounded-md border border-border px-4 py-3">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("servers.agents.stateRoot")}
                </p>
                <p className="mt-2 break-all text-foreground">
                  {selectedAgent.persistentState?.stateRootPath ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
              <div className="rounded-md border border-border px-4 py-3">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("servers.agents.memoryFile")}
                </p>
                <p className="mt-2 break-all text-foreground">
                  {selectedAgent.persistentState?.memoryPath ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
            </div>
            {canInspectPersistentFiles && selectedAgent.persistentState ? (
              <div className="space-y-3 rounded-md border border-border bg-background px-4 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {t("conversationView.colleagues.persistentFiles")}
                </p>
                <PathItem
                  label={t("conversationView.colleagues.profilePath")}
                  value={selectedAgent.persistentState.profilePath}
                />
                <PathItem
                  label={t("conversationView.colleagues.notesPath")}
                  value={selectedAgent.persistentState.notesDirPath}
                />
                <PathItem
                  label={t("conversationView.colleagues.statePath")}
                  value={selectedAgent.persistentState.stateDirPath}
                />
                <PathItem
                  label={t("conversationView.colleagues.artifactsPath")}
                  value={selectedAgent.persistentState.artifactsDirPath}
                />
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                onClick={() => onOpenDm(selectedAgent.id)}
              >
                <MessageSquare className="size-4" />
                {t("conversationView.messageAgent")}
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </aside>
  );
}

function PathItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-3">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 break-all text-sm text-foreground">{value}</p>
    </div>
  );
}

export function ExecutionDrawer({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const { t } = useT("translation");
  const { session } = useExecutionSession({ sessionId });
  const [isCancelling, setIsCancelling] = React.useState(false);
  const isSessionCancelable =
    session?.status === "running" || session?.status === "pending";

  const handleCancel = React.useCallback(async () => {
    if (!isSessionCancelable || isCancelling) {
      return;
    }
    setIsCancelling(true);
    try {
      await cancelCurrentRunAction({ sessionId });
    } catch (error) {
      console.error("[ExecutionDrawer] failed to cancel session", error);
      toast.error(t("chatInput.cancelFailed"));
    } finally {
      setIsCancelling(false);
    }
  }, [isCancelling, isSessionCancelable, sessionId, t]);

  return (
    <aside className={overlayDrawerClassName}>
      <div className={drawerHeaderClassName}>
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-xl font-semibold text-foreground">
            {t("conversationView.execution.title")}
          </p>
        </div>
        <div className={drawerHeaderActionsClassName}>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void handleCancel()}
            disabled={!isSessionCancelable || isCancelling}
          >
            {isCancelling ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Pause className="size-4" />
            )}
            {t("chatInput.cancelTask")}
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            {t("conversationView.close")}
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">
        <TaskHistoryProvider
          value={{
            refreshTasks: async () => undefined,
            touchTask: () => undefined,
          }}
        >
          <ExecutionContainer
            sessionId={sessionId}
            defaultRightPanelCollapsed
            collapsedChatContentInsetPercent={10}
            hidePresetBadge
            onCancelExecution={handleCancel}
          />
        </TaskHistoryProvider>
      </div>
    </aside>
  );
}

export function TaskDrawer({
  serverId,
  channelId,
  task,
  activity,
  members,
  agents,
  onTaskUpdated,
  onRefreshActivity,
  onClose,
}: {
  serverId: string;
  channelId: string;
  task: ChannelTask;
  activity: ChannelTaskActivityMessage[];
  members: ServerChannelMemberItem[];
  agents: ServerAgentItem[];
  onTaskUpdated: (task: ChannelTask) => void;
  onRefreshActivity: () => Promise<void>;
  onClose: () => void;
}) {
  const { t } = useT("translation");
  const [isSaving, setIsSaving] = React.useState(false);
  const updateAssignee = async (value: string) => {
    const [kind, id] = value.split(":", 2);
    setIsSaving(true);
    try {
      const nextTask = await channelTasksApi.updateTask(
        serverId,
        channelId,
        task.taskId,
        {
          title: task.title,
          description: task.description,
          assigneeUserId: kind === "user" ? id : null,
          assigneeAgentIdentityId: kind === "agent" ? id : null,
          assigneePresetId: null,
        },
      );
      onTaskUpdated(nextTask);
      await onRefreshActivity();
      toast.success(t("channelTasks.toasts.assigneeUpdated"));
    } catch (error) {
      console.error("[TaskDrawer] assignee update failed", error);
      toast.error(t("channelTasks.toasts.assigneeFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <aside className={overlayDrawerClassName}>
      <div className={drawerHeaderClassName}>
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-xl font-semibold text-foreground">{task.title}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <div className="space-y-4">
          <div className="rounded-md border border-border px-4 py-4">
            <p className="text-xs font-medium text-muted-foreground">
              {t("conversationView.taskDetail")}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="secondary">#{task.displayNumber}</Badge>
              <Badge variant="outline">
                {t("channelTasks.detail.creator")}:{" "}
                {task.creator?.label || task.creatorUserId}
              </Badge>
              <Badge variant="outline">
                {t("channelTasks.detail.assignee")}:{" "}
                {task.assignee?.label || t("channelTasks.detail.unassigned")}
              </Badge>
            </div>
            <p className="mt-2 text-sm leading-7 text-foreground">
              {task.description || t("servers.agents.emptyDescription")}
            </p>
            <label className="mt-4 block space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                {t("channelTasks.detail.assignee")}
              </span>
              <select
                value={
                  task.assigneeAgentIdentityId
                    ? `agent:${task.assigneeAgentIdentityId}`
                    : task.assigneeUserId
                      ? `user:${task.assigneeUserId}`
                      : "none:"
                }
                disabled={isSaving}
                onChange={(event) => void updateAssignee(event.target.value)}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground shadow-none"
              >
                <option value="none:">
                  {t("channelTasks.detail.unassigned")}
                </option>
                {members.map((member) => (
                  <option key={member.id} value={`user:${member.userId}`}>
                    {member.user?.displayName || member.userId}
                  </option>
                ))}
                {agents.map((agent) => (
                  <option key={agent.id} value={`agent:${agent.id}`}>
                    @{agent.handle} / {agent.displayName}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="rounded-md border border-border px-4 py-4">
            <p className="text-xs font-medium text-muted-foreground">
              {t("conversationView.taskActivity")}
            </p>
            <div className="mt-3 overflow-hidden rounded-md border border-border bg-background">
              {activity.length > 0 ? (
                activity.map((item) => (
                  <div
                    key={item.messageId}
                    className="border-b border-border last:border-b-0"
                  >
                    <MessageRow
                      message={toConversationMessage(item)}
                      agents={agents}
                      onOpenThread={() => undefined}
                      onToggleSaved={() => undefined}
                      compact
                    />
                  </div>
                ))
              ) : (
                <p className="px-3 py-3 text-sm text-muted-foreground">
                  {t("conversationView.noTaskActivity")}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

export { SharedArtifactsDrawer };
