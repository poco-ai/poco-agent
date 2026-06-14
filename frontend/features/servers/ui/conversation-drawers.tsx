"use client";

import React from "react";
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Check,
  Files,
  Info,
  Loader2,
  MessageSquare,
  Paperclip,
  Pause,
  Plus,
  SquareCheckBig,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileCard } from "@/components/shared/file-card";
import { PersistentRuntimeBadge } from "@/components/shared/persistent-runtime-badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { InputFile } from "@/features/chat/types";
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
  filterStaleComposerReferences,
  getComposerCandidateSearchText,
  getComposerDraftAttachmentReferences,
  getComposerDraftAttachments,
  getComposerTrigger,
  insertComposerCandidate,
  insertUploadedComposerReference,
  removeComposerReferenceText,
  type ComposerCandidate,
  type ComposerReference,
  upsertComposerReference,
} from "@/features/servers/lib/server-conversation-view";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { SharedArtifactsDrawer } from "@/features/servers/ui/shared-artifacts-drawer";

import { MessageRow } from "./conversation-message-row";
import { getAgentRuntimeStatus } from "../lib/agent-runtime-status";
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
  draftReferences,
  suggestedMentionHandle,
  asTask,
  onDraftChange,
  onDraftReferencesChange,
  onAsTaskChange,
  onSend,
  onUploadFiles,
  onClose,
  onOpenExecution,
  onToggleReaction,
  isSending,
  isUploading,
}: {
  thread: ServerConversationMessage[];
  serverId: string | null;
  channelId: string;
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerChannelMemberItem[];
  currentUserId?: string | null;
  draft: string;
  draftReferences: ComposerReference[];
  suggestedMentionHandle?: string | null;
  asTask: boolean;
  onDraftChange: (value: string) => void;
  onDraftReferencesChange: (value: ComposerReference[]) => void;
  onAsTaskChange: (value: boolean) => void;
  onSend: () => void;
  onUploadFiles: (files: File[]) => Promise<InputFile[]>;
  onClose: () => void;
  onOpenExecution?: (sessionId: string) => void;
  onToggleReaction?: (
    message: ServerConversationMessage,
    emoji: string,
  ) => void;
  isSending: boolean;
  isUploading?: boolean;
}) {
  const { t } = useT("translation");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const isComposingRef = React.useRef(false);
  const [selectionStart, setSelectionStart] = React.useState(0);

  const syncTextareaHeight = React.useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, []);

  React.useEffect(() => {
    syncTextareaHeight();
  }, [draft, syncTextareaHeight]);

  const composerTrigger = React.useMemo(
    () => getComposerTrigger(draft),
    [draft],
  );
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
            console.error(
              "[ThreadDrawer] load context candidates failed",
              error,
            );
            setContextCandidates([]);
          }
        });
    }, 150);
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [channelId, composerTrigger, serverId]);

  const composerCandidates = React.useMemo(
    () =>
      composerTrigger?.prefix === "@"
        ? participantCandidates.slice(0, 8)
        : contextCandidates,
    [composerTrigger?.prefix, contextCandidates, participantCandidates],
  );

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
    onDraftReferencesChange(
      upsertComposerReference(
        filterStaleComposerReferences(inserted.text, draftReferences),
        inserted.reference,
      ),
    );
    textareaRef.current?.focus();
  };

  const activeReferences = React.useMemo(
    () => filterStaleComposerReferences(draft, draftReferences),
    [draft, draftReferences],
  );
  const confirmedAttachments = React.useMemo(
    () => getComposerDraftAttachments(activeReferences),
    [activeReferences],
  );

  const handleDraftValueChange = React.useCallback(
    (nextDraft: string) => {
      onDraftChange(nextDraft);
      onDraftReferencesChange(
        filterStaleComposerReferences(nextDraft, draftReferences),
      );
    },
    [draftReferences, onDraftChange, onDraftReferencesChange],
  );

  const insertUploadedDraftReferences = React.useCallback(
    (uploadedFiles: InputFile[]) => {
      if (uploadedFiles.length === 0) return;

      const textarea = textareaRef.current;
      const initialStart = textarea?.selectionStart ?? selectionStart;
      const initialEnd = textarea?.selectionEnd ?? selectionStart;
      let nextDraft = draft;
      let nextCursor = initialStart;
      let nextReferences = [...activeReferences];

      for (const file of uploadedFiles) {
        const result = insertUploadedComposerReference(
          nextDraft,
          nextCursor,
          initialEnd,
          file,
        );
        if (!result) continue;

        nextDraft = result.text;
        nextCursor = result.cursor;
        nextReferences = upsertComposerReference(
          filterStaleComposerReferences(nextDraft, nextReferences),
          result.reference,
        );
      }

      onDraftChange(nextDraft);
      onDraftReferencesChange(nextReferences);
      setSelectionStart(nextCursor);
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(nextCursor, nextCursor);
      });
    },
    [
      activeReferences,
      draft,
      onDraftChange,
      onDraftReferencesChange,
      selectionStart,
    ],
  );

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isComposing = event.nativeEvent.isComposing || isComposingRef.current;
    const hasComposerTrigger = composerTrigger !== null;
    const selectedCandidate = composerCandidates[mentionIndex];

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
    if (
      hasComposerTrigger &&
      !isComposing &&
      (event.key === "Enter" || event.key === "Tab")
    ) {
      event.preventDefault();
      if (selectedCandidate) {
        insertCandidate(selectedCandidate);
      }
      return;
    }
    if (event.key === "Enter" && !event.shiftKey && !isComposing) {
      event.preventDefault();
      if (!isSending && (draft.trim() || confirmedAttachments.length > 0)) {
        onSend();
      }
    }
  };

  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const input = event.currentTarget;
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) {
      return;
    }
    try {
      const uploadedFiles = await onUploadFiles(files);
      insertUploadedDraftReferences(uploadedFiles);
    } finally {
      input.value = "";
    }
  };

  const handlePaste = async (
    event: React.ClipboardEvent<HTMLTextAreaElement>,
  ) => {
    const file = Array.from(event.clipboardData?.items ?? [])
      .find((item) => item.kind === "file")
      ?.getAsFile();
    if (!file) {
      return;
    }
    event.preventDefault();
    const uploadedFiles = await onUploadFiles([file]);
    insertUploadedDraftReferences(uploadedFiles);
  };

  const handleRemoveAttachment = React.useCallback(
    (index: number) => {
      const reference =
        getComposerDraftAttachmentReferences(activeReferences)[index];
      if (!reference) return;
      const result = removeComposerReferenceText(draft, reference);
      onDraftChange(result.text);
      onDraftReferencesChange(
        filterStaleComposerReferences(
          result.text,
          activeReferences.filter((item) => item.id !== reference.id),
        ),
      );
      setSelectionStart(result.cursor);
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(result.cursor, result.cursor);
      });
    },
    [activeReferences, draft, onDraftChange, onDraftReferencesChange],
  );

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
      <div className="flex min-h-0 flex-1">
        <div className="min-h-0 flex-1 overflow-y-auto">
          {thread.map((message, index) => (
            <div key={message.id}>
              <MessageRow
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
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-border px-6 py-4">
        <input
          type="file"
          multiple
          ref={fileInputRef}
          className="hidden"
          onChange={(event) => {
            void handleFileSelect(event);
          }}
        />
        {confirmedAttachments.length > 0 ? (
          <div className="mb-2 flex min-w-0 flex-wrap gap-2 px-3">
            {confirmedAttachments.map((file, index) => (
              <FileCard
                key={`${file.source}-${index}`}
                file={file}
                onRemove={() => handleRemoveAttachment(index)}
                className="w-full max-w-48 bg-background"
              />
            ))}
          </div>
        ) : null}
        {suggestedMentionHandle ? (
          <div className="mb-2 flex items-center gap-2 rounded-md border border-border bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
            <Info className="size-4 shrink-0 text-muted-foreground" />
            <span>
              {t("conversationView.threadMentionHint")}{" "}
              <span className="font-medium text-foreground">
                @{suggestedMentionHandle}
              </span>
            </span>
          </div>
        ) : null}
        <div className="relative flex w-full min-w-0 items-end gap-2 rounded-lg border border-border bg-card px-3 py-2">
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                disabled={isSending || isUploading}
                className="flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                aria-label={t("conversationView.composerActions")}
                title={t("conversationView.composerActions")}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              side="top"
              sideOffset={8}
              className="w-36"
            >
              <DropdownMenuItem
                disabled={isSending || isUploading}
                onSelect={() => fileInputRef.current?.click()}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Paperclip className="size-4" />
                )}
                <span>{t("hero.uploadFile")}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled={isSending}
                onSelect={() => onAsTaskChange(!asTask)}
              >
                <SquareCheckBig
                  className={cn("size-4", asTask ? "text-primary" : "")}
                />
                <span className="flex-1">{t("conversationView.asTask")}</span>
                {asTask ? <Check className="size-4 text-primary" /> : null}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <textarea
            ref={textareaRef}
            value={draft}
            onChange={(event) => {
              handleDraftValueChange(event.target.value);
              setSelectionStart(event.target.selectionStart);
            }}
            onClick={(event) =>
              setSelectionStart(event.currentTarget.selectionStart)
            }
            onKeyUp={(event) =>
              setSelectionStart(event.currentTarget.selectionStart)
            }
            onKeyDown={handleKeyDown}
            onInput={() => syncTextareaHeight()}
            onPaste={(event) => void handlePaste(event)}
            onCompositionStart={() => {
              isComposingRef.current = true;
            }}
            onCompositionEnd={() => {
              window.requestAnimationFrame(() => {
                isComposingRef.current = false;
              });
            }}
            rows={1}
            placeholder={t("conversationView.threadPlaceholder")}
            disabled={isSending}
            className="min-w-0 flex-1 resize-none overflow-y-auto bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 scrollbar-hide"
            style={{
              minHeight: "2rem",
              maxHeight: "10rem",
              lineHeight: "1.5rem",
            }}
          />
          <button
            type="button"
            onClick={onSend}
            disabled={
              isSending ||
              isUploading ||
              (!draft.trim() && confirmedAttachments.length === 0)
            }
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground disabled:opacity-50"
            aria-label={t("conversationView.send")}
            title={t("conversationView.send")}
          >
            {isSending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <ArrowUp className="size-4" />
            )}
          </button>
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
                    <PersistentRuntimeBadge
                      status={runtimeStatus}
                      label={t(runtimeStatus.labelKey)}
                      pinnedLabel={t("runtime.labels.pinned")}
                    />
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
                    <PersistentRuntimeBadge
                      status={selectedRuntimeStatus}
                      label={t(selectedRuntimeStatus.labelKey)}
                      pinnedLabel={t("runtime.labels.pinned")}
                    />
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
