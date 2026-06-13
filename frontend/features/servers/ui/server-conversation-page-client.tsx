"use client";

import * as React from "react";
import {
  Archive,
  ArrowDown,
  ArrowUp,
  Bot,
  Check,
  ChevronLeft,
  Files,
  Hash,
  Lock,
  LogOut,
  Loader2,
  Mic,
  MicOff,
  Paperclip,
  Plus,
  Search,
  Settings2,
  SquareCheckBig,
  Trash2,
  UserRound,
  Users,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { FileCard } from "@/components/shared/file-card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { uploadAttachment } from "@/features/attachments/api/attachment-api";
import type { FileNode, InputFile } from "@/features/chat/types";
import { channelTasksApi } from "@/features/channel-tasks/api/channel-tasks-api";
import { resolveChannelTaskView } from "@/features/channel-tasks/lib/channel-task-board";
import type {
  ChannelTask,
  ChannelTaskStatus,
  ChannelTaskView,
} from "@/features/channel-tasks/model/types";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { serversApi } from "@/features/servers";
import type {
  ServerAgentItem,
  ServerChannelItem,
  ServerChannelMemberItem,
  ServerConversationMessage,
  ServerItem,
  ServerMemberItem,
  ServerRole,
} from "@/features/servers/model/types";
import { useServerMembership } from "@/features/servers/hooks/use-server-membership";
import {
  buildAgentMentionCandidate,
  buildArtifactComposerCandidate,
  buildHumanMentionCandidates,
  buildParticipantComposerCandidate,
  buildTaskComposerCandidate,
  filterStaleComposerReferences,
  getComposerDraftAttachmentReferences,
  getComposerDraftAttachments,
  getComposerCandidateSearchText,
  getComposerTrigger,
  getAvailableChannelHumanMembers,
  getUserDisplayName,
  hasInboxSignal,
  insertComposerCandidate,
  insertUploadedComposerReference,
  removeComposerReferenceText,
  serializeComposerReferencesForSend,
  sortChannelsForSidebar,
  sortMessagesChronologically,
  type ComposerCandidate,
  type ComposerReference,
  upsertComposerReference,
} from "@/features/servers/lib/server-conversation-view";
import { getMessageSessionId } from "@/features/servers/lib/server-conversation-messages";
import {
  canManageServerMembers,
  canManageServerOperations,
  isServerRole,
} from "@/features/servers/lib/server-member-permissions";
import { getExplicitColleagueSelection } from "@/features/servers/lib/colleague-selection";
import {
  toggleMessageReaction,
  updateMessageById,
} from "@/features/servers/lib/message-reactions";
import { shouldShowServerMobileDetail } from "@/features/servers/lib/server-mobile-navigation";
import { AgentPresetDialog } from "@/features/servers/ui/agent-preset-dialog";
import { ChannelTasksWorkspace } from "@/features/servers/ui/channel-tasks-workspace";
import { ColleagueDetail } from "@/features/servers/ui/colleague-detail";
import { ColleaguesPanel } from "@/features/servers/ui/colleagues-panel";
import {
  AgentDrawer,
  ExecutionDrawer,
  SharedArtifactsDrawer,
  ThreadDrawer,
} from "@/features/servers/ui/conversation-drawers";
import {
  getMessageAuthor,
  getMessageText,
  MessageRow,
} from "@/features/servers/ui/conversation-message-row";
import {
  FeedPanel,
  SearchPanel,
} from "@/features/servers/ui/conversation-panels";
import { ServerAccessDialog } from "@/features/servers/ui/server-access-dialog";
import { ServerWorkspaceSidebar } from "@/features/servers/ui/server-workspace-sidebar";
import type {
  ColleagueSelection,
  DrawerState,
  FeedItem,
  WorkspaceMode,
} from "@/features/servers/ui/server-workspace-types";
import { useUserAccount } from "@/features/user/hooks/use-user-account";
import { appendTranscribedText, useVoiceInput } from "@/features/voice";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { playUploadSound } from "@/lib/utils/sound";

const LAST_SELECTION_KEY = "poco-servers-last-selection-v1";
const SAVED_MESSAGES_KEY = "poco-saved-messages-v1";
const READ_MESSAGES_KEY = "poco-read-messages-v1";
const MAX_FILE_SIZE = 100 * 1024 * 1024;

type CachedServerConversationContext = {
  channels: ServerChannelItem[];
  messagesByChannel: Record<string, ServerConversationMessage[]>;
  channelAgentsByChannelId: Record<string, ServerAgentItem[]>;
};

const serverConversationContextCache = new Map<
  string,
  CachedServerConversationContext
>();
let serverListCache: ServerItem[] | null = null;

function resolveWorkspaceMode(value: string | null): WorkspaceMode | null {
  if (value === "saved") {
    return "inbox";
  }
  if (
    value === "search" ||
    value === "tasks" ||
    value === "colleagues" ||
    value === "inbox"
  ) {
    return value;
  }
  return null;
}

function isDrawerCompatibleWithMode(
  drawer: DrawerState,
  mode: WorkspaceMode,
): boolean {
  if (drawer.type === "none") {
    return true;
  }
  if (mode === "search" || mode === "inbox") {
    return drawer.type === "thread" || drawer.type === "execution";
  }
  if (mode === "tasks") {
    return (
      drawer.type === "thread" ||
      drawer.type === "artifacts" ||
      drawer.type === "execution"
    );
  }
  if (mode === "colleagues") {
    return drawer.type === "colleague";
  }
  return (
    drawer.type === "thread" ||
    drawer.type === "execution" ||
    drawer.type === "agent" ||
    drawer.type === "artifacts"
  );
}

function loadSavedMessageIds(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(SAVED_MESSAGES_KEY);
    if (!raw) {
      return new Set();
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return new Set();
    }
    return new Set(parsed.filter((item) => typeof item === "string"));
  } catch {
    return new Set();
  }
}

function saveSavedMessageIds(ids: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(SAVED_MESSAGES_KEY, JSON.stringify([...ids]));
}

function loadReadMessageIds(): Set<string> {
  if (typeof window === "undefined") {
    return new Set();
  }
  try {
    const raw = window.localStorage.getItem(READ_MESSAGES_KEY);
    if (!raw) {
      return new Set();
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return new Set();
    }
    return new Set(parsed.filter((item) => typeof item === "string"));
  } catch {
    return new Set();
  }
}

function saveReadMessageIds(ids: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(READ_MESSAGES_KEY, JSON.stringify([...ids]));
}

function saveLastSelection(selection: Record<string, string | null>) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LAST_SELECTION_KEY, JSON.stringify(selection));
}

function loadLastSelection(): Record<string, string | null> | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(LAST_SELECTION_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed as Record<string, string | null>;
  } catch {
    return null;
  }
}

function getExplicitMentionHandles(value: string): string[] {
  return [...value.matchAll(/(?:^|\s)@([A-Za-z0-9._-]+)(?=$|[\s,.!?;:])/g)].map(
    (match) => match[1].trim().toLowerCase(),
  );
}

function inferThreadMentionHandle(
  thread: ServerConversationMessage[],
  agents: ServerAgentItem[],
): string | null {
  const agentHandleSet = new Set(
    agents.map((agent) => agent.handle.trim().toLowerCase()),
  );

  for (const message of thread) {
    const contentHandle =
      typeof message.content.agent_handle === "string"
        ? message.content.agent_handle.trim().toLowerCase()
        : "";
    if (contentHandle && agentHandleSet.has(contentHandle)) {
      return contentHandle;
    }

    const text = getMessageText(message);
    for (const handle of getExplicitMentionHandles(text)) {
      if (agentHandleSet.has(handle)) {
        return handle;
      }
    }

    const actorLabel =
      typeof message.content.actor_label === "string"
        ? message.content.actor_label.trim().toLowerCase()
        : "";
    if (actorLabel) {
      const matchedAgent = agents.find(
        (agent) => agent.displayName.trim().toLowerCase() === actorLabel,
      );
      if (matchedAgent) {
        return matchedAgent.handle.trim().toLowerCase();
      }
    }
  }

  return null;
}

function ChannelActionButtons({
  channel,
  memberCount,
  compact = false,
  className,
  onOpenSettings,
  onOpenMembers,
  onOpenArtifacts,
  onOpenLeaveConfirm,
}: {
  channel: ServerChannelItem | null;
  memberCount: number;
  compact?: boolean;
  className?: string;
  onOpenSettings: () => void;
  onOpenMembers: () => void;
  onOpenArtifacts: () => void;
  onOpenLeaveConfirm: () => void;
}) {
  const { t } = useT("translation");
  const iconButtonClassName = compact ? "size-9 px-0" : undefined;
  const isSystemChannel = Boolean(
    channel?.isSystemChannel || channel?.systemChannelType,
  );

  return (
    <div className={cn("flex shrink-0 items-center gap-2", className)}>
      <Button
        type="button"
        variant="outline"
        size={compact ? "icon" : "sm"}
        className={iconButtonClassName}
        onClick={onOpenSettings}
        aria-label={t("common.settings")}
        title={t("common.settings")}
      >
        <Settings2 className="size-4" />
      </Button>
      {!isSystemChannel ? (
        <Button
          type="button"
          variant="outline"
          size={compact ? "icon" : "sm"}
          className={iconButtonClassName}
          onClick={onOpenLeaveConfirm}
          disabled={!channel}
          aria-label={t("conversationView.leave")}
          title={t("conversationView.leave")}
        >
          <LogOut className="size-4" />
        </Button>
      ) : null}
      <Button
        type="button"
        variant="outline"
        size={compact ? "icon" : "sm"}
        className={iconButtonClassName}
        onClick={onOpenArtifacts}
        disabled={!channel}
        aria-label={t("conversationView.sharedArtifacts.title")}
        title={t("conversationView.sharedArtifacts.title")}
      >
        <Files className="size-4" />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className={compact ? "h-9 px-2.5" : undefined}
        onClick={onOpenMembers}
        aria-label={t("conversationView.members.title")}
        title={t("conversationView.members.title")}
      >
        <Users className="size-4" />
        <span className="tabular-nums">{memberCount}</span>
      </Button>
    </div>
  );
}

function ConversationContent({
  channel,
  agents,
  presets,
  members,
  messages,
  savedMessageIds,
  draft,
  draftReferences,
  asTask,
  isLoading,
  isUploading,
  onDraftChange,
  onDraftReferencesChange,
  onAsTaskChange,
  onSend,
  onUploadFiles,
  onOpenThread,
  onOpenSettings,
  onOpenMembers,
  onOpenArtifacts,
  onOpenLeaveConfirm,
  onToggleSaved,
  onToggleReaction,
  onOpenExecution,
  onOpenAgentProfile,
  isSending,
  currentUserId,
}: {
  channel: ServerChannelItem | null;
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerChannelMemberItem[];
  messages: ServerConversationMessage[];
  savedMessageIds: Set<string>;
  draft: string;
  draftReferences: ComposerReference[];
  asTask: boolean;
  isLoading: boolean;
  isUploading: boolean;
  onDraftChange: (value: string) => void;
  onDraftReferencesChange: (value: ComposerReference[]) => void;
  onAsTaskChange: (value: boolean) => void;
  onSend: () => void;
  onUploadFiles: (files: File[]) => Promise<InputFile[]>;
  onOpenThread: (message: ServerConversationMessage) => void;
  onOpenSettings: () => void;
  onOpenMembers: () => void;
  onOpenArtifacts: () => void;
  onOpenLeaveConfirm: () => void;
  onToggleSaved: (messageId: string) => void;
  onToggleReaction: (message: ServerConversationMessage, emoji: string) => void;
  onOpenExecution: (sessionId: string) => void;
  onOpenAgentProfile: (agentId: string) => void;
  isSending: boolean;
  currentUserId?: string | null;
}) {
  const { t } = useT("translation");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const isComposingRef = React.useRef(false);
  const Icon = channel?.conversationType === "direct_message" ? Lock : Hash;
  const scrollContainerRef = React.useRef<HTMLDivElement | null>(null);
  const hasInitializedScrollRef = React.useRef(false);
  const lastMessageCountRef = React.useRef(messages.length);
  const [selectionStart, setSelectionStart] = React.useState(0);
  const composerTrigger = React.useMemo(
    () => getComposerTrigger(draft),
    [draft],
  );
  const [showScrollButton, setShowScrollButton] = React.useState(false);
  const [isUserScrolling, setIsUserScrolling] = React.useState(false);
  const draftRef = React.useRef(draft);
  const lng = useLanguage();
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
    if (!channel || composerTrigger?.prefix !== "#") {
      setContextCandidates([]);
      return;
    }
    let cancelled = false;
    const timeoutId = window.setTimeout(() => {
      void Promise.all([
        serversApi.listChannelArtifactCandidates(channel.serverId, channel.id, {
          q: composerTrigger.query,
          limit: 6,
        }),
        channelTasksApi.listTaskCandidates(channel.serverId, channel.id, {
          q: composerTrigger.query,
          limit: 6,
        }),
      ])
        .then(([artifacts, taskCandidates]) => {
          if (cancelled) {
            return;
          }
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
              "[ConversationContent] load context candidates failed",
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
  }, [channel, composerTrigger]);

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

  React.useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

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

  const activeReferences = React.useMemo(
    () => filterStaleComposerReferences(draft, draftReferences),
    [draft, draftReferences],
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
        syncTextareaHeight();
      });
    },
    [
      activeReferences,
      draft,
      onDraftChange,
      onDraftReferencesChange,
      selectionStart,
      syncTextareaHeight,
    ],
  );

  const handleVoiceTranscription = React.useCallback(
    (text: string) => {
      onDraftChange(appendTranscribedText(draftRef.current, text));
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        syncTextareaHeight();
      });
    },
    [onDraftChange, syncTextareaHeight],
  );

  const voiceInput = useVoiceInput({
    t,
    language: lng,
    onTranscription: handleVoiceTranscription,
  });
  const confirmedAttachments = React.useMemo(
    () => getComposerDraftAttachments(activeReferences),
    [activeReferences],
  );

  const scrollToBottom = React.useCallback(
    (behavior: ScrollBehavior = "smooth") => {
      const element = scrollContainerRef.current;
      if (!element) {
        return false;
      }
      window.requestAnimationFrame(() => {
        element.scrollTo({ top: element.scrollHeight, behavior });
        setIsUserScrolling(false);
        setShowScrollButton(false);
      });
      return true;
    },
    [],
  );

  React.useEffect(() => {
    hasInitializedScrollRef.current = false;
    lastMessageCountRef.current = 0;
    setIsUserScrolling(false);
    setShowScrollButton(false);
  }, [channel?.id]);

  React.useEffect(() => {
    const element = scrollContainerRef.current;
    if (!element) {
      return;
    }

    let timeoutId: number | null = null;
    const handleScroll = () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      timeoutId = window.setTimeout(() => {
        const distanceFromBottom =
          element.scrollHeight - element.scrollTop - element.clientHeight;
        const isNearBottom = distanceFromBottom < 100;
        setIsUserScrolling(!isNearBottom);
        setShowScrollButton(!isNearBottom);
      }, 80);
    };

    handleScroll();
    element.addEventListener("scroll", handleScroll);
    return () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
      element.removeEventListener("scroll", handleScroll);
    };
  }, [channel?.id]);

  React.useEffect(() => {
    if (messages.length === 0 || hasInitializedScrollRef.current) {
      return;
    }
    if (scrollToBottom("auto")) {
      hasInitializedScrollRef.current = true;
    }
  }, [isLoading, messages.length, scrollToBottom]);

  React.useEffect(() => {
    const hasNewMessages = messages.length > lastMessageCountRef.current;
    lastMessageCountRef.current = messages.length;
    if (!hasNewMessages) {
      return;
    }
    if (!isUserScrolling) {
      scrollToBottom("smooth");
    } else {
      setShowScrollButton(true);
    }
  }, [isUserScrolling, messages.length, scrollToBottom]);

  const insertCandidate = (candidate: ComposerCandidate) => {
    if (!composerTrigger) {
      return;
    }
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

  const handleTextareaKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
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
      if (
        !isSending &&
        !isUploading &&
        !voiceInput.isBusy &&
        (draft.trim() || confirmedAttachments.length > 0)
      ) {
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
    const items = event.clipboardData?.items;
    if (!items) {
      return;
    }
    const file = Array.from(items)
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
        syncTextareaHeight();
      });
    },
    [
      activeReferences,
      draft,
      onDraftChange,
      onDraftReferencesChange,
      syncTextareaHeight,
    ],
  );

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="hidden border-b border-border px-6 py-5 md:block">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex items-center gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-md border border-border bg-primary/15 text-foreground">
              <Icon className="size-6" />
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-2xl font-semibold text-foreground">
                {channel?.name ?? t("conversationView.loading")}
              </h2>
            </div>
          </div>
          <ChannelActionButtons
            channel={channel}
            memberCount={members.length + agents.length}
            onOpenSettings={onOpenSettings}
            onOpenMembers={onOpenMembers}
            onOpenArtifacts={onOpenArtifacts}
            onOpenLeaveConfirm={onOpenLeaveConfirm}
          />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-background">
        {isLoading ? (
          <div className="space-y-4 px-6 py-6">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-24 rounded-md" />
            ))}
          </div>
        ) : (
          <div className="relative min-h-0 flex-1 overflow-hidden">
            <div className="flex h-full min-h-0">
              <div
                ref={scrollContainerRef}
                className="h-full min-h-0 min-w-0 flex-1 overflow-y-auto"
              >
                {messages.map((message, index) => (
                  <div key={message.id}>
                    <MessageRow
                      message={message}
                      agents={agents}
                      members={members}
                      presets={presets}
                      defaultExpanded={index === messages.length - 1}
                      onOpenThread={() => onOpenThread(message)}
                      onOpenExecution={onOpenExecution}
                      onOpenAgentProfile={onOpenAgentProfile}
                      isSaved={savedMessageIds.has(message.id)}
                      onToggleSaved={() => onToggleSaved(message.id)}
                      onToggleReaction={(emoji) =>
                        onToggleReaction(message, emoji)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
            {showScrollButton ? (
              <div className="absolute bottom-6 right-6 z-10 animate-in fade-in slide-in-from-bottom-4 duration-300">
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => scrollToBottom("smooth")}
                  className="size-10 rounded-full bg-background shadow-lg transition-shadow hover:shadow-xl"
                  title={t("chat.scrollToLatestMessage")}
                >
                  <ArrowDown className="size-5" />
                </Button>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div className="border-t border-border px-6 py-4">
        <input
          type="file"
          multiple
          ref={fileInputRef}
          className="hidden"
          onChange={(event) => void handleFileSelect(event)}
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
              const nextDraft = event.target.value;
              handleDraftValueChange(nextDraft);
              setSelectionStart(event.target.selectionStart);
            }}
            onClick={(event) =>
              setSelectionStart(event.currentTarget.selectionStart)
            }
            onKeyUp={(event) =>
              setSelectionStart(event.currentTarget.selectionStart)
            }
            onKeyDown={handleTextareaKeyDown}
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
            placeholder={t("conversationView.messagePlaceholder", {
              name: channel?.name ?? "",
            })}
            disabled={isSending}
            className="min-w-0 flex-1 resize-none overflow-y-auto bg-transparent py-1 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 scrollbar-hide"
            style={{
              minHeight: "2rem",
              maxHeight: "10rem",
              lineHeight: "1.5rem",
            }}
          />
          {voiceInput.isSupported ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => {
                    void voiceInput.toggleRecording();
                  }}
                  disabled={
                    isSending ||
                    isUploading ||
                    voiceInput.status === "transcribing"
                  }
                  className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                    voiceInput.status === "recording"
                      ? "animate-pulse bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      : "text-muted-foreground hover:bg-accent",
                  )}
                  aria-label={
                    voiceInput.status === "transcribing"
                      ? t("hero.transcribingVoiceInput")
                      : voiceInput.status === "recording"
                        ? t("hero.stopVoiceInput")
                        : t("hero.startVoiceInput")
                  }
                >
                  {voiceInput.status === "transcribing" ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : voiceInput.status === "recording" ? (
                    <MicOff className="size-4" />
                  ) : (
                    <Mic className="size-4" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>
                {voiceInput.status === "transcribing"
                  ? t("hero.transcribingVoiceInput")
                  : voiceInput.status === "recording"
                    ? t("hero.stopVoiceInput")
                    : t("hero.startVoiceInput")}
              </TooltipContent>
            </Tooltip>
          ) : null}
          <button
            type="button"
            onClick={onSend}
            disabled={
              isSending ||
              isUploading ||
              voiceInput.isBusy ||
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
    </section>
  );
}

function CreateChannelDialog({
  open,
  agents,
  members,
  currentUserId,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  agents: ServerAgentItem[];
  members: ServerMemberItem[];
  currentUserId?: string | null;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: {
    name: string;
    description: string;
    memberUserIds: string[];
    agentIdentityIds: string[];
  }) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [memberSearch, setMemberSearch] = React.useState("");
  const [selectedHumanIds, setSelectedHumanIds] = React.useState<Set<string>>(
    () => new Set(),
  );
  const [selectedAgentIds, setSelectedAgentIds] = React.useState<Set<string>>(
    () => new Set(),
  );
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setName("");
      setDescription("");
      setMemberSearch("");
      setSelectedHumanIds(new Set());
      setSelectedAgentIds(new Set());
      setIsSubmitting(false);
    }
  }, [open]);

  const keyword = memberSearch.trim().toLowerCase();
  const visibleAgents = agents.filter((agent) => {
    if (!keyword) {
      return true;
    }
    return `${agent.displayName} ${agent.handle}`
      .toLowerCase()
      .includes(keyword);
  });
  const visibleMembers = members
    .filter(
      (member) => member.status === "active" && member.userId !== currentUserId,
    )
    .filter((member) => {
      if (!keyword) {
        return true;
      }
      return `${getUserDisplayName(member.user, member.userId)} ${member.userId}`
        .toLowerCase()
        .includes(keyword);
    });

  const toggleSelected = (
    setter: React.Dispatch<React.SetStateAction<Set<string>>>,
    id: string,
  ) => {
    setter((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim()) {
      return;
    }
    setIsSubmitting(true);
    try {
      await onCreate({
        name,
        description,
        memberUserIds: Array.from(selectedHumanIds),
        agentIdentityIds: Array.from(selectedAgentIds),
      });
      onOpenChange(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-2 border-border p-0 shadow-[var(--shadow-lg)] sm:rounded-md">
        <form onSubmit={(event) => void handleSubmit(event)}>
          <DialogHeader className="border-b border-border px-6 py-5 text-left">
            <DialogTitle className="text-lg font-semibold uppercase tracking-[0.08em]">
              {t("conversationView.createChannel.title")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5 px-6 py-5">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground">
                {t("conversationView.createChannel.name")}{" "}
                <span className="text-primary">*</span>
              </label>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t(
                  "conversationView.createChannel.namePlaceholder",
                )}
                className="h-11 rounded-none border-2 border-border bg-background text-base shadow-none"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground">
                {t("conversationView.createChannel.description")}{" "}
                <span className="text-muted-foreground">
                  {t("conversationView.createChannel.optional")}
                </span>
              </label>
              <Textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder={t(
                  "conversationView.createChannel.descriptionPlaceholder",
                )}
                rows={3}
                className="rounded-none border-2 border-border bg-background text-base shadow-none"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-[0.16em] text-foreground">
                {t("conversationView.createChannel.members")}{" "}
                <span className="text-muted-foreground">
                  {t("conversationView.createChannel.optional")}
                </span>
              </label>
              <div className="flex h-11 items-center gap-2 border-2 border-border bg-background px-3">
                <Search className="size-4 text-muted-foreground" />
                <input
                  value={memberSearch}
                  onChange={(event) => setMemberSearch(event.target.value)}
                  placeholder={t(
                    "conversationView.createChannel.memberSearchPlaceholder",
                  )}
                  className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                />
              </div>
              <div className="max-h-72 overflow-y-auto border-2 border-border bg-background p-2">
                <div className="px-2 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {t("conversationView.members.agents")}
                </div>
                <div className="space-y-1">
                  {visibleAgents.map((agent) => {
                    const selected = selectedAgentIds.has(agent.id);
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        onClick={() =>
                          toggleSelected(setSelectedAgentIds, agent.id)
                        }
                        className={cn(
                          "flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors",
                          selected
                            ? "bg-primary/15 text-foreground"
                            : "hover:bg-muted/30",
                        )}
                      >
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
                          <Bot className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1 truncate">
                          {agent.displayName || agent.handle}
                        </span>
                        {selected ? (
                          <Check className="size-4 text-primary" />
                        ) : null}
                      </button>
                    );
                  })}
                  {visibleAgents.length === 0 ? (
                    <p className="px-3 py-2 text-sm text-muted-foreground">
                      {t("conversationView.members.noAgents")}
                    </p>
                  ) : null}
                </div>
                <div className="mt-3 px-2 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {t("conversationView.members.humans")}
                </div>
                <div className="space-y-1">
                  {visibleMembers.map((member) => {
                    const selected = selectedHumanIds.has(member.userId);
                    return (
                      <button
                        key={member.userId}
                        type="button"
                        onClick={() =>
                          toggleSelected(setSelectedHumanIds, member.userId)
                        }
                        className={cn(
                          "flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors",
                          selected
                            ? "bg-primary/15 text-foreground"
                            : "hover:bg-muted/30",
                        )}
                      >
                        <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
                          <UserRound className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1 truncate">
                          {getUserDisplayName(member.user, member.userId)}
                        </span>
                        {selected ? (
                          <Check className="size-4 text-primary" />
                        ) : null}
                      </button>
                    );
                  })}
                  {visibleMembers.length === 0 ? (
                    <p className="px-3 py-2 text-sm text-muted-foreground">
                      {t("conversationView.members.noHumans")}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
          <DialogFooter className="grid grid-cols-2 gap-2 border-t border-border px-6 py-5">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              {t("conversationView.createChannel.create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ChannelSettingsDialog({
  open,
  channel,
  isArchiving,
  onOpenChange,
  onSave,
  onArchive,
  onDelete,
}: {
  open: boolean;
  channel: ServerChannelItem | null;
  isArchiving: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (input: { name: string; description: string }) => void;
  onArchive: () => void;
  onDelete: () => void;
}) {
  const { t } = useT("translation");
  const [name, setName] = React.useState(channel?.name ?? "");
  const [description, setDescription] = React.useState(
    channel?.description ?? "",
  );
  const isSystemChannel = Boolean(
    channel?.isSystemChannel || channel?.systemChannelType,
  );

  React.useEffect(() => {
    if (open) {
      setName(channel?.name ?? "");
      setDescription(channel?.description ?? "");
    }
  }, [channel?.description, channel?.name, open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("conversationView.channelSettings.title")}
          </DialogTitle>
          <DialogDescription>
            {t("conversationView.channelSettings.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              {t("conversationView.channelSettings.name")}
            </label>
            <Input
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={isSystemChannel}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              {t("conversationView.channelSettings.channelDescription")}
            </label>
            <Textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              placeholder={t(
                "conversationView.channelSettings.descriptionPlaceholder",
              )}
              className="rounded-md border-border bg-background shadow-none"
              disabled={isSystemChannel}
            />
          </div>
        </div>
        <DialogFooter className="flex-row items-center justify-between sm:justify-between">
          {!isSystemChannel ? (
            <div className="flex min-w-0 flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onArchive}
                disabled={isArchiving || !channel}
              >
                <Archive className="size-4" />
                {t("conversationView.channelSettings.archive")}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onDelete}
                disabled={!channel}
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
              >
                <Trash2 className="size-4" />
                {t("conversationView.channelSettings.delete")}
              </Button>
            </div>
          ) : (
            <div />
          )}
          <Button
            type="button"
            size="sm"
            onClick={() => onSave({ name, description })}
            disabled={!name.trim() || isSystemChannel}
          >
            {t("conversationView.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ChannelMembersDialog({
  open,
  channel,
  agents,
  availableAgents,
  availableHumans,
  humans,
  canManageMembers,
  onOpenChange,
  onOpenDm,
  onAddAgents,
  onAddMembers,
  onRemoveAgent,
  onRemoveMember,
}: {
  open: boolean;
  channel: ServerChannelItem | null;
  agents: ServerAgentItem[];
  availableAgents: ServerAgentItem[];
  availableHumans: ServerMemberItem[];
  humans: ServerChannelMemberItem[];
  canManageMembers: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenDm: (agentId: string) => void;
  onAddAgents: (agentIds: string[]) => Promise<void>;
  onAddMembers: (userIds: string[]) => Promise<void>;
  onRemoveAgent: (agentId: string) => void;
  onRemoveMember: (membershipId: number) => void;
}) {
  const { t } = useT("translation");
  const [activePane, setActivePane] = React.useState<"agents" | "humans">(
    "agents",
  );
  const [agentSearch, setAgentSearch] = React.useState("");
  const [humanSearch, setHumanSearch] = React.useState("");
  const [selectedAgentIds, setSelectedAgentIds] = React.useState<Set<string>>(
    () => new Set(),
  );
  const [selectedHumanIds, setSelectedHumanIds] = React.useState<Set<string>>(
    () => new Set(),
  );
  const [isAddingAgents, setIsAddingAgents] = React.useState(false);
  const [isAddingHumans, setIsAddingHumans] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setAgentSearch("");
      setHumanSearch("");
      setSelectedAgentIds(new Set());
      setSelectedHumanIds(new Set());
      setIsAddingAgents(false);
      setIsAddingHumans(false);
      setActivePane("agents");
    }
  }, [open]);

  const visibleAvailableAgents = React.useMemo(() => {
    const keyword = agentSearch.trim().toLowerCase();
    return availableAgents.filter((agent) => {
      if (!keyword) {
        return true;
      }
      return `${agent.displayName} ${agent.handle}`
        .toLowerCase()
        .includes(keyword);
    });
  }, [agentSearch, availableAgents]);

  const visibleAvailableHumans = React.useMemo(() => {
    const keyword = humanSearch.trim().toLowerCase();
    return availableHumans.filter((member) => {
      if (!keyword) {
        return true;
      }
      return `${getUserDisplayName(member.user, member.userId)} ${member.userId}`
        .toLowerCase()
        .includes(keyword);
    });
  }, [availableHumans, humanSearch]);

  const toggleAgentSelection = (agentId: string) => {
    setSelectedAgentIds((current) => {
      const next = new Set(current);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  };

  const toggleHumanSelection = (userId: string) => {
    setSelectedHumanIds((current) => {
      const next = new Set(current);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  const handleAddAgents = async () => {
    if (!canManageMembers || selectedAgentIds.size === 0) {
      return;
    }
    setIsAddingAgents(true);
    try {
      await onAddAgents(Array.from(selectedAgentIds));
      setSelectedAgentIds(new Set());
      setAgentSearch("");
    } finally {
      setIsAddingAgents(false);
    }
  };

  const handleAddHumans = async () => {
    if (selectedHumanIds.size === 0) {
      return;
    }
    setIsAddingHumans(true);
    try {
      await onAddMembers(Array.from(selectedHumanIds));
      setSelectedHumanIds(new Set());
      setHumanSearch("");
    } finally {
      setIsAddingHumans(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("conversationView.members.title")}</DialogTitle>
          <DialogDescription>
            {t("conversationView.members.description", {
              channel: channel?.name ?? t("conversationView.loading"),
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <ToggleGroup
            type="single"
            value={activePane}
            onValueChange={(value) => {
              if (value === "agents" || value === "humans") {
                setActivePane(value);
              }
            }}
            variant="outline"
            size="sm"
            className="inline-flex w-fit justify-start rounded-md bg-muted/30 p-1"
          >
            <ToggleGroupItem value="agents" className="gap-2 px-3">
              <Bot className="size-4" />
              {t("conversationView.members.agents")}
              <span className="text-xs tabular-nums text-muted-foreground">
                {agents.length}
              </span>
            </ToggleGroupItem>
            <ToggleGroupItem value="humans" className="gap-2 px-3">
              <UserRound className="size-4" />
              {t("conversationView.members.humans")}
              <span className="text-xs tabular-nums text-muted-foreground">
                {humans.length}
              </span>
            </ToggleGroupItem>
          </ToggleGroup>

          {activePane === "agents" ? (
            <section className="space-y-4">
              <div className="space-y-2">
                {agents.length > 0 ? (
                  agents.map((agent) => (
                    <div
                      key={agent.id}
                      className="group/member-item flex items-center gap-3 rounded-md border border-border bg-card px-3 py-3 transition-colors hover:bg-muted/20"
                    >
                      <button
                        type="button"
                        onClick={() => onOpenDm(agent.id)}
                        className="flex min-w-0 flex-1 items-center gap-3 text-left"
                      >
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                          <Bot className="size-4" />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-foreground">
                            {agent.displayName}
                          </span>
                          <span className="block truncate text-xs text-muted-foreground">
                            @{agent.handle}
                          </span>
                        </span>
                        {agent.description ? (
                          <span className="hidden max-w-[45%] shrink-0 text-right text-xs leading-5 text-muted-foreground sm:block">
                            <span className="line-clamp-2 opacity-0 transition-opacity group-hover/member-item:opacity-100 group-focus-within/member-item:opacity-100">
                              {agent.description}
                            </span>
                          </span>
                        ) : null}
                      </button>
                      {canManageMembers ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-8 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => onRemoveAgent(agent.id)}
                          aria-label={t("conversationView.members.removeAgent")}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
                    {t("conversationView.members.noAgents")}
                  </div>
                )}
              </div>
              <div className="space-y-3 rounded-md border border-border bg-card px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">
                    {t("conversationView.members.inviteAgents")}
                  </p>
                  <span className="text-xs text-muted-foreground">
                    {visibleAvailableAgents.length}
                  </span>
                </div>
                <Input
                  value={agentSearch}
                  onChange={(event) => setAgentSearch(event.target.value)}
                  placeholder={t(
                    "conversationView.members.agentSearchPlaceholder",
                  )}
                  disabled={!canManageMembers}
                />
                <div className="max-h-72 overflow-y-auto space-y-1">
                  {visibleAvailableAgents.length > 0 ? (
                    visibleAvailableAgents.map((agent) => {
                      const selected = selectedAgentIds.has(agent.id);
                      return (
                        <button
                          key={agent.id}
                          type="button"
                          onClick={() => toggleAgentSelection(agent.id)}
                          disabled={!canManageMembers}
                          className={cn(
                            "group/member-item flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm transition-colors",
                            selected
                              ? "bg-primary/15 text-foreground"
                              : "hover:bg-muted/30",
                            !canManageMembers &&
                              "cursor-not-allowed opacity-60",
                          )}
                        >
                          <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
                            <Bot className="size-4" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-foreground">
                              {agent.displayName}
                            </span>
                            <span className="block truncate text-xs text-muted-foreground">
                              @{agent.handle}
                            </span>
                          </span>
                          {agent.description ? (
                            <span className="hidden max-w-[42%] shrink-0 text-right text-xs leading-5 text-muted-foreground sm:block">
                              <span className="line-clamp-2 opacity-0 transition-opacity group-hover/member-item:opacity-100 group-focus-within/member-item:opacity-100">
                                {agent.description}
                              </span>
                            </span>
                          ) : null}
                          {selected ? (
                            <Check className="size-4 shrink-0 text-primary" />
                          ) : null}
                        </button>
                      );
                    })
                  ) : (
                    <div className="rounded-md border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
                      {t("conversationView.members.noAvailableAgents")}
                    </div>
                  )}
                </div>
                <Button
                  type="button"
                  onClick={() => void handleAddAgents()}
                  disabled={
                    !canManageMembers ||
                    selectedAgentIds.size === 0 ||
                    isAddingAgents
                  }
                >
                  <Plus className="size-4" />
                  {t("conversationView.members.addSelectedAgents")}
                </Button>
                {!canManageMembers ? (
                  <p className="text-xs text-muted-foreground">
                    {t("conversationView.members.manageAgentsPermissionHint")}
                  </p>
                ) : null}
              </div>
            </section>
          ) : (
            <section className="space-y-4">
              <div className="space-y-2">
                {humans.length > 0 ? (
                  humans.map((human) => (
                    <div
                      key={human.id}
                      className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-3 transition-colors hover:bg-muted/20"
                    >
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                        <UserRound className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-foreground">
                          {getUserDisplayName(human.user, human.userId)}
                        </span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {human.role}
                        </span>
                      </span>
                      {canManageMembers && human.role !== "owner" ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="ml-auto size-8 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => onRemoveMember(human.id)}
                          aria-label={t("conversationView.members.removeHuman")}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="rounded-md border border-dashed border-border px-3 py-8 text-center text-sm text-muted-foreground">
                    {t("conversationView.members.noHumans")}
                  </div>
                )}
              </div>
              <div className="space-y-3 rounded-md border border-border bg-card px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">
                    {t("conversationView.members.inviteHumans")}
                  </p>
                  <span className="text-xs text-muted-foreground">
                    {visibleAvailableHumans.length}
                  </span>
                </div>
                <Input
                  value={humanSearch}
                  onChange={(event) => setHumanSearch(event.target.value)}
                  placeholder={t(
                    "conversationView.members.humanSearchPlaceholder",
                  )}
                />
                <div className="max-h-72 overflow-y-auto space-y-1">
                  {visibleAvailableHumans.length > 0 ? (
                    visibleAvailableHumans.map((human) => {
                      const selected = selectedHumanIds.has(human.userId);
                      return (
                        <button
                          key={human.userId}
                          type="button"
                          onClick={() => toggleHumanSelection(human.userId)}
                          className={cn(
                            "flex w-full items-center gap-3 rounded-md px-3 py-3 text-left text-sm transition-colors",
                            selected
                              ? "bg-primary/15 text-foreground"
                              : "hover:bg-muted/30",
                          )}
                        >
                          <span className="flex size-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted">
                            <UserRound className="size-4" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-foreground">
                              {getUserDisplayName(human.user, human.userId)}
                            </span>
                            <span className="block truncate text-xs text-muted-foreground">
                              {human.userId}
                            </span>
                          </span>
                          {selected ? (
                            <Check className="size-4 shrink-0 text-primary" />
                          ) : null}
                        </button>
                      );
                    })
                  ) : (
                    <div className="rounded-md border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
                      {t("conversationView.members.noAvailableHumans")}
                    </div>
                  )}
                </div>
                <Button
                  type="button"
                  onClick={() => void handleAddHumans()}
                  disabled={selectedHumanIds.size === 0 || isAddingHumans}
                >
                  <Plus className="size-4" />
                  {t("conversationView.members.addSelectedHumans")}
                </Button>
              </div>
            </section>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function ServerConversationPageClient({
  serverId,
  channelId,
}: {
  serverId?: string | null;
  channelId?: string | null;
}) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";
  const router = useRouter();
  const searchParams = useSearchParams();
  const routeServerParam = searchParams.get("server");
  const routeModeParam = searchParams.get("mode");
  const routeViewParam = searchParams.get("view");
  const { profile } = useUserAccount();
  const initialSelectedServerId =
    serverId ??
    routeServerParam ??
    loadLastSelection()?.serverId ??
    serverListCache?.[0]?.id ??
    null;
  const cachedServerContext = initialSelectedServerId
    ? serverConversationContextCache.get(initialSelectedServerId)
    : null;

  const [servers, setServers] = React.useState<ServerItem[]>(
    () => serverListCache ?? [],
  );
  const [selectedServerId, setSelectedServerId] = React.useState<string | null>(
    initialSelectedServerId,
  );
  const [channels, setChannels] = React.useState<ServerChannelItem[]>(
    () => cachedServerContext?.channels ?? [],
  );
  const [messagesByChannel, setMessagesByChannel] = React.useState<
    Record<string, ServerConversationMessage[]>
  >(() => cachedServerContext?.messagesByChannel ?? {});
  const [channelAgents, setChannelAgents] = React.useState<ServerAgentItem[]>(
    [],
  );
  const [channelAgentsByChannelId, setChannelAgentsByChannelId] =
    React.useState<Record<string, ServerAgentItem[]>>(
      () => cachedServerContext?.channelAgentsByChannelId ?? {},
    );
  const [channelMembers, setChannelMembers] = React.useState<
    ServerChannelMemberItem[]
  >([]);
  const [tasks, setTasks] = React.useState<ChannelTask[]>([]);
  const [threadMessages, setThreadMessages] = React.useState<
    ServerConversationMessage[]
  >([]);
  const [channelArtifacts, setChannelArtifacts] = React.useState<FileNode[]>(
    [],
  );
  const [draft, setDraft] = React.useState("");
  const [draftReferences, setDraftReferences] = React.useState<
    ComposerReference[]
  >([]);
  const [threadDraft, setThreadDraft] = React.useState("");
  const [threadDraftReferences, setThreadDraftReferences] = React.useState<
    ComposerReference[]
  >([]);
  const [searchValue, setSearchValue] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(!cachedServerContext);
  const [isSending, setIsSending] = React.useState(false);
  const [isUploadingDraftFile, setIsUploadingDraftFile] = React.useState(false);
  const [asTask, setAsTask] = React.useState(false);
  const [threadAsTask, setThreadAsTask] = React.useState(false);
  const [savedMessageIds, setSavedMessageIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [readMessageIds, setReadMessageIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [mode, setMode] = React.useState<WorkspaceMode>(
    resolveWorkspaceMode(routeModeParam) ??
      (channelId ? "conversation" : "search"),
  );
  const [isDesktop, setIsDesktop] = React.useState(false);
  const [isMobileDetailVisible, setIsMobileDetailVisible] = React.useState(() =>
    shouldShowServerMobileDetail({
      isDesktop: false,
      channelId,
      modeFromUrl: resolveWorkspaceMode(routeModeParam),
    }),
  );
  const [taskView, setTaskView] = React.useState<ChannelTaskView>(
    resolveChannelTaskView(routeViewParam),
  );
  const [drawer, setDrawer] = React.useState<DrawerState>({ type: "none" });
  const [desktopDrawerRatio, setDesktopDrawerRatio] = React.useState(50);
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [membersOpen, setMembersOpen] = React.useState(false);
  const [serverAccessOpen, setServerAccessOpen] = React.useState(false);
  const [createChannelOpen, setCreateChannelOpen] = React.useState(false);
  const [leaveChannelOpen, setLeaveChannelOpen] = React.useState(false);
  const [agentPresetOpen, setAgentPresetOpen] = React.useState(false);
  const [isArchivingChannel, setIsArchivingChannel] = React.useState(false);
  const [isLeavingChannel, setIsLeavingChannel] = React.useState(false);

  const syncServers = React.useCallback((nextServers: ServerItem[]) => {
    serverListCache = nextServers;
    setServers(nextServers);
  }, []);

  const switchServer = React.useCallback(
    (nextServerId: string) => {
      setSelectedServerId(nextServerId);
      saveLastSelection({
        mode: "search",
        serverId: nextServerId,
        channelId: null,
      });
      setServerAccessOpen(false);
      router.push(`/${lng}/servers?mode=search&server=${nextServerId}`);
    },
    [lng, router],
  );

  const {
    serverAgents,
    serverMembers,
    serverInvites,
    presets,
    isServerAccessWorking,
    isAgentCreating,
    createServer,
    acceptInvite,
    createInvite,
    copyInvite,
    createAgent,
    updateAgentDescription,
    updateMemberRole,
    transferOwnership,
    removeMember,
    refreshMembership,
  } = useServerMembership({
    selectedServerId,
    onServersChanged: syncServers,
    onSwitchServer: switchServer,
    onSelectAgent: (agent) => {
      setDrawer({
        type: "colleague",
        selection: { kind: "agent", id: agent.id },
      });
      setAgentPresetOpen(false);
    },
    onClearSelection: () => setDrawer({ type: "colleague", selection: null }),
  });

  const activeChannelId = channelId ?? null;
  const selectedServer =
    servers.find((server) => server.id === selectedServerId) ?? null;
  const selectedChannel =
    channels.find(
      (channel) =>
        channel.id === activeChannelId && channel.serverId === selectedServerId,
    ) ?? null;
  const topLevelChannels = sortChannelsForSidebar(
    channels.filter((channel) => channel.conversationType === "channel"),
  );
  const directMessages = channels.filter(
    (channel) => channel.conversationType === "direct_message",
  );
  const currentMessages = React.useMemo(
    () =>
      activeChannelId
        ? sortMessagesChronologically(messagesByChannel[activeChannelId] ?? [])
        : [],
    [activeChannelId, messagesByChannel],
  );
  const threadMentionHandle = React.useMemo(
    () => inferThreadMentionHandle(threadMessages, channelAgents),
    [channelAgents, threadMessages],
  );
  const knownAgents = React.useMemo(() => {
    const byId = new Map<string, ServerAgentItem>();
    const append = (agent: ServerAgentItem | null | undefined) => {
      if (agent) {
        byId.set(agent.id, agent);
      }
    };
    serverAgents.forEach(append);
    channelAgents.forEach(append);
    Object.values(messagesByChannel).forEach((messages) => {
      messages.forEach((message) => append(message.authorAgent));
    });
    threadMessages.forEach((message) => append(message.authorAgent));
    return Array.from(byId.values());
  }, [channelAgents, messagesByChannel, serverAgents, threadMessages]);
  const contentAreaRef = React.useRef<HTMLDivElement | null>(null);
  const isResizingDrawerRef = React.useRef(false);
  const hasDesktopDrawer = drawer.type !== "none";
  const feedModeActive = mode === "search" || mode === "inbox";
  const tasksModeActive = Boolean(channelId) && mode === "tasks";
  const colleaguesModeActive = mode === "colleagues";
  const showMobileBack = !isDesktop && isMobileDetailVisible;
  const showMobileChannelActions = showMobileBack && mode === "conversation";
  const colleagueSelection = React.useMemo<ColleagueSelection | null>(() => {
    return getExplicitColleagueSelection(drawer);
  }, [drawer]);
  const colleagueDirectoryAgents = React.useMemo(
    () =>
      serverAgents.filter(
        (agent) => !agent.removedAt && agent.lifecycleState !== "removed",
      ),
    [serverAgents],
  );
  const availableChannelAgents = React.useMemo(() => {
    const existingIds = new Set(channelAgents.map((agent) => agent.id));
    return serverAgents.filter((agent) => !existingIds.has(agent.id));
  }, [channelAgents, serverAgents]);
  const availableChannelHumans = React.useMemo(
    () => getAvailableChannelHumanMembers(serverMembers, channelMembers),
    [channelMembers, serverMembers],
  );
  const currentServerMembership = React.useMemo(() => {
    if (!profile?.id) {
      return null;
    }
    return (
      serverMembers.find(
        (member) => member.userId === profile.id && member.status === "active",
      ) ?? null
    );
  }, [profile?.id, serverMembers]);
  const isChannelOwner = Boolean(
    selectedChannel &&
    profile?.id &&
    (selectedChannel.createdBy === profile.id ||
      channelMembers.some(
        (member) => member.userId === profile.id && member.role === "owner",
      )),
  );
  const currentServerRole = React.useMemo<ServerRole | null>(() => {
    if (isServerRole(currentServerMembership?.role)) {
      return currentServerMembership.role;
    }
    if (profile?.id && selectedServer?.ownerUserId === profile.id) {
      return "owner";
    }
    return null;
  }, [currentServerMembership?.role, profile?.id, selectedServer?.ownerUserId]);
  const canManageServerOps = canManageServerOperations(currentServerRole);
  const canManageServerMemberRoles = canManageServerMembers(currentServerRole);

  const allFeedItems = React.useMemo<FeedItem[]>(() => {
    return channels
      .flatMap((channel) =>
        (messagesByChannel[channel.id] ?? []).map((message) => ({
          channel,
          message,
        })),
      )
      .sort((left, right) => {
        return (
          Date.parse(right.message.createdAt) -
          Date.parse(left.message.createdAt)
        );
      });
  }, [channels, messagesByChannel]);

  const channelIdBySessionId = React.useMemo(() => {
    const mapping = new Map<string, string>();
    for (const [channelId, messages] of Object.entries(messagesByChannel)) {
      for (const message of messages) {
        const sessionId = getMessageSessionId(message);
        if (!sessionId || mapping.has(sessionId)) {
          continue;
        }
        mapping.set(sessionId, channelId);
      }
    }
    return mapping;
  }, [messagesByChannel]);

  const activeChannelIdByAgentId = React.useMemo(
    () =>
      Object.fromEntries(
        serverAgents.map((agent) => [
          agent.id,
          agent.persistentState?.activeSessionId
            ? (channelIdBySessionId.get(
                agent.persistentState.activeSessionId,
              ) ?? "")
            : "",
        ]),
      ),
    [channelIdBySessionId, serverAgents],
  );
  const channelNamesByAgentId = React.useMemo(() => {
    const mapping: Record<string, string[]> = {};
    for (const channel of channels) {
      for (const agent of channelAgentsByChannelId[channel.id] ?? []) {
        mapping[agent.id] = [...(mapping[agent.id] ?? []), channel.name];
      }
    }
    return mapping;
  }, [channelAgentsByChannelId, channels]);

  const filteredSearchItems = React.useMemo(() => {
    const keyword = searchValue.trim().toLowerCase();
    if (!keyword) {
      return [];
    }
    return allFeedItems.filter((item) => {
      const haystack =
        `${item.channel.name} ${getMessageText(item.message)} ${getMessageAuthor(item.message)}`.toLowerCase();
      return haystack.includes(keyword);
    });
  }, [allFeedItems, searchValue]);

  const inboxItems = React.useMemo(
    () =>
      allFeedItems.filter((item) => hasInboxSignal(item.message, profile?.id)),
    [allFeedItems, profile?.id],
  );
  const unreadInboxItems = React.useMemo(
    () => inboxItems.filter((item) => !readMessageIds.has(item.message.id)),
    [inboxItems, readMessageIds],
  );
  const savedItems = React.useMemo(
    () => allFeedItems.filter((item) => savedMessageIds.has(item.message.id)),
    [allFeedItems, savedMessageIds],
  );

  const loadServers = React.useCallback(async () => {
    const nextServers = await serversApi.listServers();
    syncServers(nextServers);

    const requestedServerId = serverId || routeServerParam;
    const lastSelection = loadLastSelection();
    const preferredServerId =
      requestedServerId ||
      lastSelection?.serverId ||
      nextServers[0]?.id ||
      null;
    setSelectedServerId(preferredServerId);
  }, [routeServerParam, serverId, syncServers]);

  React.useEffect(() => {
    const lastSelection = loadLastSelection();
    const routeMode = resolveWorkspaceMode(routeModeParam);
    if (routeMode) {
      setMode(routeMode);
    } else if (!channelId && lastSelection?.mode) {
      setMode(
        lastSelection.mode === "channel" || lastSelection.mode === "dm"
          ? "search"
          : (lastSelection.mode as WorkspaceMode),
      );
    } else if (!channelId) {
      setMode("search");
    } else {
      setMode("conversation");
    }
  }, [channelId, routeModeParam]);

  React.useEffect(() => {
    setSavedMessageIds(loadSavedMessageIds());
    setReadMessageIds(loadReadMessageIds());
    void loadServers();
  }, [loadServers]);

  const markMessagesRead = React.useCallback((messageIds: string[]) => {
    if (messageIds.length === 0) {
      return;
    }
    setReadMessageIds((current) => {
      const next = new Set(current);
      let changed = false;
      for (const messageId of messageIds) {
        if (!messageId || next.has(messageId)) {
          continue;
        }
        next.add(messageId);
        changed = true;
      }
      if (changed) {
        saveReadMessageIds(next);
      }
      return changed ? next : current;
    });
  }, []);

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }
    const mediaQuery = window.matchMedia("(min-width: 768px)");

    const updateMatches = (matches: boolean) => {
      setIsDesktop(matches);
      setIsMobileDetailVisible(
        shouldShowServerMobileDetail({
          isDesktop: matches,
          channelId,
          modeFromUrl: resolveWorkspaceMode(routeModeParam),
        }),
      );
    };

    updateMatches(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      updateMatches(event.matches);
    };

    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }

    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, [channelId, routeModeParam]);

  React.useEffect(() => {
    let cancelled = false;

    const loadServerContext = async () => {
      if (!selectedServerId) {
        setChannels([]);
        setMessagesByChannel({});
        setChannelAgentsByChannelId({});
        setTasks([]);
        setChannelAgents([]);
        setChannelMembers([]);
        setChannelArtifacts([]);
        return;
      }
      const cachedContext =
        serverConversationContextCache.get(selectedServerId) ?? null;
      if (cachedContext) {
        setChannels(cachedContext.channels);
        setMessagesByChannel(cachedContext.messagesByChannel);
        setChannelAgentsByChannelId(cachedContext.channelAgentsByChannelId);
        setIsLoading(false);
      } else {
        setChannels([]);
        setMessagesByChannel({});
        setChannelAgentsByChannelId({});
        setTasks([]);
        setChannelAgents([]);
        setChannelMembers([]);
        setChannelArtifacts([]);
        setIsLoading(true);
      }
      try {
        const nextChannels = await serversApi.listChannels(selectedServerId);
        if (cancelled) {
          return;
        }
        setChannels(nextChannels);

        const previews = await Promise.all(
          nextChannels.map(async (channel) => {
            const messages = await serversApi.listMessages(
              selectedServerId,
              channel.id,
            );
            return [channel.id, messages] as const;
          }),
        );
        setMessagesByChannel(Object.fromEntries(previews));
        const channelAgentEntries = await Promise.all(
          nextChannels.map(async (channel) => {
            const agents = await serversApi.listChannelAgents(
              selectedServerId,
              channel.id,
            );
            return [channel.id, agents] as const;
          }),
        );
        if (cancelled) {
          return;
        }
        const nextChannelAgentsByChannelId =
          Object.fromEntries(channelAgentEntries);
        setChannelAgentsByChannelId(nextChannelAgentsByChannelId);
        serverConversationContextCache.set(selectedServerId, {
          channels: nextChannels,
          messagesByChannel: Object.fromEntries(previews),
          channelAgentsByChannelId: nextChannelAgentsByChannelId,
        });
      } catch (error) {
        console.error("[ServersWorkspace] load failed", error);
        toast.error(t("conversationView.toasts.loadFailed"));
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadServerContext();
    return () => {
      cancelled = true;
    };
  }, [selectedServerId, t]);

  React.useEffect(() => {
    const loadActiveChannelContext = async () => {
      if (!selectedServerId || !activeChannelId || !selectedChannel) {
        setTasks([]);
        setChannelAgents([]);
        setChannelMembers([]);
        setChannelArtifacts([]);
        return;
      }
      try {
        const [nextTasks, nextMembers, nextArtifacts] = await Promise.all([
          channelTasksApi.listTasks(selectedServerId, activeChannelId),
          serversApi.listChannelMembers(selectedServerId, activeChannelId),
          serversApi.listChannelArtifacts(selectedServerId, activeChannelId),
        ]);
        setTasks(nextTasks);
        setChannelAgents(channelAgentsByChannelId[activeChannelId] ?? []);
        setChannelMembers(nextMembers);
        setChannelArtifacts(nextArtifacts);
      } catch (error) {
        console.error("[ServersWorkspace] active channel load failed", error);
        toast.error(t("conversationView.toasts.loadFailed"));
      }
    };

    void loadActiveChannelContext();
  }, [
    activeChannelId,
    channelAgentsByChannelId,
    selectedChannel,
    selectedServerId,
    t,
  ]);

  React.useEffect(() => {
    setDraftReferences([]);
    setIsUploadingDraftFile(false);
  }, [activeChannelId]);

  React.useEffect(() => {
    if (!selectedServerId || channels.length === 0) {
      return;
    }
    serverConversationContextCache.set(selectedServerId, {
      channels,
      messagesByChannel,
      channelAgentsByChannelId,
    });
  }, [channelAgentsByChannelId, channels, messagesByChannel, selectedServerId]);

  React.useEffect(() => {
    setDrawer((current) =>
      isDrawerCompatibleWithMode(current, mode) ? current : { type: "none" },
    );
  }, [mode]);

  React.useEffect(() => {
    const lastSelection = loadLastSelection();
    if (
      !channelId &&
      isDesktop &&
      selectedServerId &&
      lastSelection?.serverId === selectedServerId &&
      (lastSelection.mode === "channel" || lastSelection.mode === "dm") &&
      lastSelection.channelId
    ) {
      router.replace(
        `/${lng}/servers/${selectedServerId}/channels/${lastSelection.channelId}?tab=chat`,
      );
    }
  }, [channelId, isDesktop, lng, router, selectedServerId]);

  React.useEffect(() => {
    if (!selectedServerId || !activeChannelId || channels.length === 0) {
      return;
    }
    const hasLoadedSelectedServerChannels = channels.every(
      (channel) => channel.serverId === selectedServerId,
    );
    if (!hasLoadedSelectedServerChannels) {
      return;
    }
    if (
      channels.some(
        (channel) =>
          channel.id === activeChannelId &&
          channel.serverId === selectedServerId,
      )
    ) {
      return;
    }
    saveLastSelection({
      mode: "search",
      serverId: selectedServerId,
      channelId: null,
    });
    router.replace(`/${lng}/servers?mode=search&server=${selectedServerId}`);
  }, [activeChannelId, channels, lng, router, selectedServerId]);

  React.useEffect(() => {
    const loadThread = async () => {
      if (drawer.type !== "thread" || !selectedServerId) {
        setThreadMessages([]);
        return;
      }
      try {
        setThreadMessages(
          await serversApi.getThread(
            selectedServerId,
            drawer.channelId,
            drawer.rootMessageId,
          ),
        );
      } catch (error) {
        console.error("[ServersWorkspace] thread load failed", error);
        toast.error(t("conversationView.toasts.threadFailed"));
      }
    };

    void loadThread();
  }, [drawer, selectedServerId, t]);

  React.useEffect(() => {
    if (currentMessages.length === 0 || mode === "inbox" || mode === "search") {
      return;
    }
    markMessagesRead(currentMessages.map((message) => message.id));
  }, [currentMessages, markMessagesRead, mode]);

  React.useEffect(() => {
    if (drawer.type !== "thread" || threadMessages.length === 0) {
      return;
    }
    markMessagesRead(threadMessages.map((message) => message.id));
  }, [drawer, markMessagesRead, threadMessages]);

  React.useEffect(() => {
    if (!selectedServerId || !activeChannelId || !selectedChannel) {
      return;
    }

    let cancelled = false;
    let inFlight = false;

    const refreshActiveChannelSnapshot = async () => {
      if (cancelled || inFlight) {
        return;
      }
      inFlight = true;
      try {
        const requests: Promise<unknown>[] = [
          serversApi.listMessages(selectedServerId, activeChannelId),
          serversApi.listChannelArtifacts(selectedServerId, activeChannelId),
        ];
        if (mode === "tasks") {
          requests.push(
            channelTasksApi.listTasks(selectedServerId, activeChannelId),
          );
        }
        if (drawer.type === "thread" && drawer.channelId === activeChannelId) {
          requests.push(
            serversApi.getThread(
              selectedServerId,
              drawer.channelId,
              drawer.rootMessageId,
            ),
          );
        }
        const [nextMessages, nextArtifacts, nextTasks, nextThread] =
          await Promise.all(requests);

        if (cancelled) {
          return;
        }
        setMessagesByChannel((current) => ({
          ...current,
          [activeChannelId]: nextMessages as ServerConversationMessage[],
        }));
        setChannelArtifacts(nextArtifacts as FileNode[]);
        if (mode === "tasks" && Array.isArray(nextTasks)) {
          setTasks(nextTasks as ChannelTask[]);
        }
        if (drawer.type === "thread" && Array.isArray(nextThread)) {
          setThreadMessages(nextThread as ServerConversationMessage[]);
        }
      } catch (error) {
        if (!cancelled) {
          console.error(
            "[ServersWorkspace] active channel refresh failed",
            error,
          );
        }
      } finally {
        inFlight = false;
      }
    };

    void refreshActiveChannelSnapshot();
    const intervalId = window.setInterval(refreshActiveChannelSnapshot, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [activeChannelId, drawer, mode, selectedChannel, selectedServerId]);

  const openMode = (nextMode: WorkspaceMode) => {
    setMode(nextMode);
    setIsMobileDetailVisible(true);
    if (nextMode === "conversation" || !selectedServerId) {
      return;
    }
    saveLastSelection({
      mode: nextMode,
      serverId: selectedServerId,
      channelId: null,
    });
    const targetUrl = activeChannelId
      ? `/${lng}/servers/${selectedServerId}/channels/${activeChannelId}?tab=chat&mode=${nextMode}`
      : `/${lng}/servers?mode=${nextMode}&server=${selectedServerId}`;
    router.replace(targetUrl, { scroll: false });
  };

  const openTaskMode = () => {
    if (!selectedServerId) {
      return;
    }
    setIsMobileDetailVisible(true);
    const targetChannelId =
      activeChannelId ??
      selectedChannel?.id ??
      topLevelChannels[0]?.id ??
      channels[0]?.id ??
      null;
    if (!targetChannelId) {
      setMode("tasks");
      return;
    }
    setMode("tasks");
    saveLastSelection({
      mode: "tasks",
      serverId: selectedServerId,
      channelId: targetChannelId,
    });
    router.replace(
      `/${lng}/servers/${selectedServerId}/channels/${targetChannelId}?tab=chat&mode=tasks&view=${taskView}`,
      { scroll: false },
    );
  };

  const updateTaskView = (nextView: ChannelTaskView) => {
    setTaskView(nextView);
    if (!selectedServerId || !activeChannelId) {
      return;
    }
    router.replace(
      `/${lng}/servers/${selectedServerId}/channels/${activeChannelId}?tab=chat&mode=tasks&view=${nextView}`,
      { scroll: false },
    );
  };

  const openChannel = React.useCallback(
    (channel: ServerChannelItem) => {
      if (!selectedServerId) {
        return;
      }
      setMode("conversation");
      setIsMobileDetailVisible(true);
      saveLastSelection({
        mode: channel.conversationType === "direct_message" ? "dm" : "channel",
        serverId: selectedServerId,
        channelId: channel.id,
      });
      router.push(
        `/${lng}/servers/${selectedServerId}/channels/${channel.id}?tab=chat`,
      );
    },
    [lng, router, selectedServerId],
  );

  const openChannelById = React.useCallback(
    (targetChannelId: string) => {
      const targetChannel = channels.find(
        (channel) => channel.id === targetChannelId,
      );
      if (!targetChannel) {
        return;
      }
      openChannel(targetChannel);
    },
    [channels, openChannel],
  );

  const uploadConversationDraftFiles = React.useCallback(
    async (files: File[], existingAttachments: InputFile[]) => {
      if (files.length === 0) {
        return [];
      }

      const existingNames = new Set(
        existingAttachments
          .map((item) => (item.name || "").trim().toLowerCase())
          .filter(Boolean),
      );
      setIsUploadingDraftFile(true);
      const uploadedFiles: InputFile[] = [];
      try {
        for (const file of files) {
          if (file.size > MAX_FILE_SIZE) {
            toast.error(t("hero.toasts.fileTooLarge"));
            continue;
          }

          const normalizedName = file.name.trim().toLowerCase();
          if (existingNames.has(normalizedName)) {
            toast.error(
              t("hero.toasts.duplicateFileName", { name: file.name }),
            );
            continue;
          }

          try {
            const uploadedFile = await uploadAttachment(file);
            uploadedFiles.push(uploadedFile);
            existingNames.add(normalizedName);
            toast.success(t("hero.toasts.uploadSuccess"));
            playUploadSound();
          } catch (error) {
            console.error("[ServersWorkspace] channel upload failed", error);
            toast.error(t("hero.toasts.uploadFailed"));
          }
        }
      } finally {
        setIsUploadingDraftFile(false);
      }

      return uploadedFiles;
    },
    [t],
  );

  const uploadDraftFiles = React.useCallback(
    async (files: File[]) =>
      uploadConversationDraftFiles(
        files,
        getComposerDraftAttachments(draftReferences),
      ),
    [draftReferences, uploadConversationDraftFiles],
  );

  const uploadThreadDraftFiles = React.useCallback(
    async (files: File[]) =>
      uploadConversationDraftFiles(
        files,
        getComposerDraftAttachments(threadDraftReferences),
      ),
    [threadDraftReferences, uploadConversationDraftFiles],
  );

  const deleteSharedArtifact = React.useCallback(
    async (file: FileNode) => {
      if (!selectedServerId || !activeChannelId || !file.artifact_id) {
        return;
      }

      try {
        await serversApi.deleteChannelArtifact(
          selectedServerId,
          activeChannelId,
          file.artifact_id,
        );
        const [nextArtifacts, nextMessages] = await Promise.all([
          serversApi.listChannelArtifacts(selectedServerId, activeChannelId),
          serversApi.listMessages(selectedServerId, activeChannelId),
        ]);
        setChannelArtifacts(nextArtifacts);
        setMessagesByChannel((current) => ({
          ...current,
          [activeChannelId]: nextMessages,
        }));
        toast.success(t("fileSidebar.deleteSuccess"));
      } catch (error) {
        console.error(
          "[ServersWorkspace] channel artifact delete failed",
          error,
        );
        toast.error(t("fileSidebar.deleteFailed"));
      }
    },
    [activeChannelId, selectedServerId, t],
  );

  const handleSend = async () => {
    if (!selectedServerId || !activeChannelId) {
      return;
    }
    const content = draft.trim();
    const serialized = serializeComposerReferencesForSend(
      content,
      draftReferences,
    );
    const entities = serialized.entities;
    const confirmedAttachments = serialized.attachments;
    if (!content && confirmedAttachments.length === 0) {
      return;
    }
    setIsSending(true);
    try {
      if (asTask) {
        const message = await serversApi.sendMessage(
          selectedServerId,
          activeChannelId,
          {
            text: content,
            attachments: confirmedAttachments,
            entities: entities.length > 0 ? entities : undefined,
            asTask: true,
          },
        );
        const title =
          content.split("\n")[0]?.trim().slice(0, 80) ||
          confirmedAttachments[0]?.name.slice(0, 80) ||
          content.slice(0, 80);
        await channelTasksApi.createTask(selectedServerId, activeChannelId, {
          title,
          description:
            content || confirmedAttachments.map((item) => item.name).join("\n"),
          sourceMessageId: message.id,
        });
        toast.success(t("conversationView.toasts.taskCreated"));
      } else {
        await serversApi.sendMessage(selectedServerId, activeChannelId, {
          text: content,
          attachments: confirmedAttachments,
          entities: entities.length > 0 ? entities : undefined,
        });
      }
      setDraft("");
      setDraftReferences([]);
      setAsTask(false);
      const messages = await serversApi.listMessages(
        selectedServerId,
        activeChannelId,
      );
      setMessagesByChannel((current) => ({
        ...current,
        [activeChannelId]: messages,
      }));
      if (asTask) {
        setTasks(
          await channelTasksApi.listTasks(selectedServerId, activeChannelId),
        );
      }
    } catch (error) {
      console.error("[ServersWorkspace] send failed", error);
      toast.error(t("conversationView.toasts.sendFailed"));
    } finally {
      setIsSending(false);
    }
  };

  const handleReply = async () => {
    if (drawer.type !== "thread" || !selectedServerId) {
      return;
    }
    const trimmedDraft = threadDraft.trim();
    const serialized = serializeComposerReferencesForSend(
      trimmedDraft,
      threadDraftReferences,
    );
    const entities = serialized.entities;
    const confirmedAttachments = serialized.attachments;
    if (!trimmedDraft && confirmedAttachments.length === 0) {
      return;
    }
    setIsSending(true);
    try {
      if (threadAsTask) {
        const explicitMentions = getExplicitMentionHandles(trimmedDraft);
        const replyText =
          threadMentionHandle && !explicitMentions.includes(threadMentionHandle)
            ? `@${threadMentionHandle} ${trimmedDraft}`
            : trimmedDraft;
        const message = await serversApi.sendMessage(
          selectedServerId,
          drawer.channelId,
          {
            text: replyText,
            attachments: confirmedAttachments,
            entities: entities.length > 0 ? entities : undefined,
            threadRootMessageId: drawer.rootMessageId,
            asTask: true,
          },
        );
        const title =
          trimmedDraft.split("\n")[0]?.trim().slice(0, 80) ||
          trimmedDraft.slice(0, 80);
        await channelTasksApi.createTask(selectedServerId, drawer.channelId, {
          title,
          description:
            trimmedDraft ||
            confirmedAttachments
              .map((attachment) => attachment.name)
              .join("\n"),
          sourceMessageId: message.id,
        });
        setThreadDraft("");
        setThreadDraftReferences([]);
        setThreadAsTask(false);
        setTasks(
          await channelTasksApi.listTasks(selectedServerId, drawer.channelId),
        );
        const messages = await serversApi.listMessages(
          selectedServerId,
          drawer.channelId,
        );
        setMessagesByChannel((current) => ({
          ...current,
          [drawer.channelId]: messages,
        }));
        toast.success(t("conversationView.toasts.taskCreated"));
      } else {
        const explicitMentions = getExplicitMentionHandles(trimmedDraft);
        const replyText =
          threadMentionHandle && !explicitMentions.includes(threadMentionHandle)
            ? `@${threadMentionHandle} ${trimmedDraft}`
            : trimmedDraft;
        await serversApi.sendMessage(selectedServerId, drawer.channelId, {
          text: replyText,
          attachments: confirmedAttachments,
          entities: entities.length > 0 ? entities : undefined,
          threadRootMessageId: drawer.rootMessageId,
        });
        setThreadDraft("");
        setThreadDraftReferences([]);
        const [messages, thread] = await Promise.all([
          serversApi.listMessages(selectedServerId, drawer.channelId),
          serversApi.getThread(
            selectedServerId,
            drawer.channelId,
            drawer.rootMessageId,
          ),
        ]);
        setMessagesByChannel((current) => ({
          ...current,
          [drawer.channelId]: messages,
        }));
        setThreadMessages(thread);
      }
    } catch (error) {
      console.error("[ServersWorkspace] reply failed", error);
      toast.error(t("conversationView.toasts.replyFailed"));
    } finally {
      setIsSending(false);
    }
  };

  const openTaskThread = (taskId: string) => {
    const task = tasks.find((item) => item.taskId === taskId);
    if (!task?.threadRootMessageId) {
      toast.error(t("conversationView.toasts.threadFailed"));
      return;
    }
    setDrawer({
      type: "thread",
      channelId: task.channelId,
      rootMessageId: task.threadRootMessageId,
    });
  };

  const updateTaskAssignee = async (
    task: ChannelTask,
    value: {
      assigneeUserId: string | null;
      assigneeAgentIdentityId: string | null;
    },
  ) => {
    try {
      const nextTask = await channelTasksApi.updateTask(
        selectedServerId ?? task.serverId,
        task.channelId,
        task.taskId,
        {
          assigneeUserId: value.assigneeUserId,
          assigneeAgentIdentityId: value.assigneeAgentIdentityId,
          assigneePresetId: null,
        },
      );
      setTasks((current) =>
        current.map((item) =>
          item.taskId === nextTask.taskId ? nextTask : item,
        ),
      );
      if (
        drawer.type === "thread" &&
        nextTask.threadRootMessageId &&
        drawer.rootMessageId === nextTask.threadRootMessageId
      ) {
        setThreadMessages(
          await serversApi.getThread(
            selectedServerId ?? nextTask.serverId,
            nextTask.channelId,
            nextTask.threadRootMessageId,
          ),
        );
      }
      toast.success(t("channelTasks.toasts.assigneeUpdated"));
    } catch (error) {
      console.error("[ServersWorkspace] task assignee update failed", error);
      toast.error(t("channelTasks.toasts.assigneeFailed"));
      throw error;
    }
  };

  const updateTaskStatus = async (
    task: ChannelTask,
    status: ChannelTaskStatus,
  ) => {
    try {
      const nextTask = await channelTasksApi.updateTaskStatus(
        selectedServerId ?? task.serverId,
        task.channelId,
        task.taskId,
        {
          status,
          position: task.position,
        },
      );
      setTasks((current) =>
        current.map((item) =>
          item.taskId === nextTask.taskId ? nextTask : item,
        ),
      );
      if (
        drawer.type === "thread" &&
        nextTask.threadRootMessageId &&
        drawer.rootMessageId === nextTask.threadRootMessageId
      ) {
        setThreadMessages(
          await serversApi.getThread(
            selectedServerId ?? nextTask.serverId,
            nextTask.channelId,
            nextTask.threadRootMessageId,
          ),
        );
      }
      toast.success(t("channelTasks.toasts.statusUpdated"));
    } catch (error) {
      console.error("[ServersWorkspace] task status update failed", error);
      toast.error(t("channelTasks.toasts.statusFailed"));
      throw error;
    }
  };

  const handleOpenDm = async (agentId: string) => {
    if (!selectedServerId) {
      return;
    }
    try {
      const dm = await serversApi.createDirectMessage(selectedServerId, {
        targetAgentIdentityId: agentId,
      });
      setChannels((current) => {
        const nextById = new Map(
          current.map((channel) => [channel.id, channel]),
        );
        nextById.set(dm.id, dm);
        return Array.from(nextById.values());
      });
      openChannel(dm);
    } catch (error) {
      console.error("[ServersWorkspace] create dm failed", error);
      toast.error(t("conversationView.toasts.dmFailed"));
    }
  };

  const handleCreateChannel = async (input: {
    name: string;
    description: string;
    memberUserIds: string[];
    agentIdentityIds: string[];
  }) => {
    if (!selectedServerId) {
      return;
    }
    const normalizedName = input.name.trim().toLowerCase();
    if (normalizedName === "public" || normalizedName === "personal") {
      toast.error(t("conversationView.toasts.systemChannelNameReserved"));
      throw new Error("Reserved system channel name");
    }
    try {
      const channel = await serversApi.createChannel(selectedServerId, {
        name: input.name.trim(),
        description: input.description.trim() || null,
        memberUserIds: input.memberUserIds,
        agentIdentityIds: input.agentIdentityIds,
      });
      setChannels((current) => [...current, channel]);
      setMessagesByChannel((current) => ({
        ...current,
        [channel.id]: [],
      }));
      toast.success(t("conversationView.toasts.channelCreated"));
      openChannel(channel);
    } catch (error) {
      console.error("[ServersWorkspace] create channel failed", error);
      toast.error(t("conversationView.toasts.channelCreateFailed"));
      throw error;
    }
  };

  const handleLeaveChannel = async () => {
    if (
      !selectedServerId ||
      !activeChannelId ||
      selectedChannel?.isSystemChannel ||
      selectedChannel?.systemChannelType
    ) {
      return;
    }
    setIsLeavingChannel(true);
    try {
      await serversApi.leaveChannel(selectedServerId, activeChannelId);
      setChannels((current) =>
        current.filter((channel) => channel.id !== activeChannelId),
      );
      setMessagesByChannel((current) => {
        const next = { ...current };
        delete next[activeChannelId];
        return next;
      });
      setLeaveChannelOpen(false);
      saveLastSelection({
        mode: "search",
        serverId: selectedServerId,
        channelId: null,
      });
      router.replace(`/${lng}/servers?mode=search&server=${selectedServerId}`);
      toast.success(
        t(
          isChannelOwner
            ? "conversationView.toasts.channelDissolved"
            : "conversationView.toasts.channelLeft",
        ),
      );
    } catch (error) {
      console.error("[ServersWorkspace] leave channel failed", error);
      toast.error(t("conversationView.toasts.channelLeaveFailed"));
    } finally {
      setIsLeavingChannel(false);
    }
  };

  const toggleSaved = (messageId: string) => {
    setSavedMessageIds((current) => {
      const next = new Set(current);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      saveSavedMessageIds(next);
      return next;
    });
  };

  const applyMessageUpdate = React.useCallback(
    (
      messageId: string,
      update: (message: ServerConversationMessage) => ServerConversationMessage,
    ) => {
      setMessagesByChannel((current) =>
        Object.fromEntries(
          Object.entries(current).map(([channelId, messages]) => [
            channelId,
            updateMessageById(messages, messageId, update),
          ]),
        ),
      );
      setThreadMessages((current) =>
        updateMessageById(current, messageId, update),
      );
    },
    [],
  );

  const handleToggleReaction = React.useCallback(
    async (message: ServerConversationMessage, emoji: string) => {
      if (!selectedServerId) {
        return;
      }
      const wasReacted = (message.reactions ?? []).some(
        (reaction) => reaction.emoji === emoji && reaction.reactedByCurrentUser,
      );
      const currentUser = profile
        ? {
            userId: profile.id,
            displayName: profile.displayName,
            avatarUrl: profile.avatar,
          }
        : null;
      applyMessageUpdate(message.id, (item) =>
        toggleMessageReaction(item, emoji, currentUser),
      );
      try {
        if (wasReacted) {
          await serversApi.removeMessageReaction(
            selectedServerId,
            message.channelId,
            message.id,
            emoji,
          );
        } else {
          await serversApi.addMessageReaction(
            selectedServerId,
            message.channelId,
            message.id,
            emoji,
          );
        }
      } catch (error) {
        console.error("[ServersWorkspace] reaction update failed", error);
        applyMessageUpdate(message.id, () => message);
        toast.error(t("conversationView.toasts.reactionFailed"));
      }
    },
    [applyMessageUpdate, profile, selectedServerId, t],
  );

  const handleArchiveChannel = async () => {
    if (
      !selectedServerId ||
      !activeChannelId ||
      selectedChannel?.isSystemChannel ||
      selectedChannel?.systemChannelType
    ) {
      return;
    }
    setIsArchivingChannel(true);
    try {
      const archived = await serversApi.archiveChannel(
        selectedServerId,
        activeChannelId,
      );
      setChannels((current) =>
        current.map((channel) =>
          channel.id === archived.id ? archived : channel,
        ),
      );
      setSettingsOpen(false);
      toast.success(t("conversationView.toasts.channelArchived"));
    } catch (error) {
      console.error("[ServersWorkspace] archive channel failed", error);
      toast.error(t("conversationView.toasts.channelArchiveFailed"));
    } finally {
      setIsArchivingChannel(false);
    }
  };

  const handleUpdateChannel = async (input: {
    name: string;
    description: string;
  }) => {
    if (
      !selectedServerId ||
      !activeChannelId ||
      selectedChannel?.isSystemChannel ||
      selectedChannel?.systemChannelType
    ) {
      return;
    }
    try {
      const updated = await serversApi.updateChannel(
        selectedServerId,
        activeChannelId,
        {
          name: input.name.trim(),
          description: input.description.trim(),
        },
      );
      setChannels((current) =>
        current.map((channel) =>
          channel.id === updated.id ? updated : channel,
        ),
      );
      setSettingsOpen(false);
      toast.success(t("conversationView.toasts.channelUpdated"));
    } catch (error) {
      console.error("[ServersWorkspace] update channel failed", error);
      toast.error(t("conversationView.toasts.channelUpdateFailed"));
    }
  };

  const handleDeleteChannel = async () => {
    if (
      !selectedServerId ||
      !activeChannelId ||
      selectedChannel?.isSystemChannel ||
      selectedChannel?.systemChannelType
    ) {
      return;
    }
    try {
      await serversApi.deleteChannel(selectedServerId, activeChannelId);
      setChannels((current) =>
        current.filter((channel) => channel.id !== activeChannelId),
      );
      setSettingsOpen(false);
      saveLastSelection({
        mode: "search",
        serverId: selectedServerId,
        channelId: null,
      });
      router.replace(`/${lng}/servers?mode=search&server=${selectedServerId}`);
      toast.success(t("conversationView.toasts.channelDeleted"));
    } catch (error) {
      console.error("[ServersWorkspace] delete channel failed", error);
      toast.error(t("conversationView.toasts.channelDeleteFailed"));
    }
  };

  const handleAddChannelMembers = async (userIds: string[]) => {
    const nextUserIds = userIds.map((userId) => userId.trim()).filter(Boolean);
    if (!selectedServerId || !activeChannelId || nextUserIds.length === 0) {
      return;
    }
    try {
      const members = await Promise.all(
        nextUserIds.map((userId) =>
          serversApi.addChannelMember(selectedServerId, activeChannelId, {
            userId,
          }),
        ),
      );
      setChannelMembers((current) => {
        const nextById = new Map(current.map((item) => [item.id, item]));
        for (const member of members) {
          nextById.set(member.id, member);
        }
        return Array.from(nextById.values());
      });
      toast.success(t("conversationView.toasts.memberAdded"));
    } catch (error) {
      console.error("[ServersWorkspace] add channel member failed", error);
      toast.error(t("conversationView.toasts.memberAddFailed"));
    }
  };

  const handleAddChannelAgents = async (agentIds: string[]) => {
    if (!selectedServerId || !activeChannelId || agentIds.length === 0) {
      return;
    }
    try {
      await Promise.all(
        agentIds.map((agentIdentityId) =>
          serversApi.addAgentToChannel(selectedServerId, activeChannelId, {
            agentIdentityId,
          }),
        ),
      );
      const nextAgents = await serversApi.listChannelAgents(
        selectedServerId,
        activeChannelId,
      );
      setChannelAgents(nextAgents);
      setChannelAgentsByChannelId((current) => ({
        ...current,
        [activeChannelId]: nextAgents,
      }));
      toast.success(t("conversationView.toasts.agentAdded"));
    } catch (error) {
      console.error("[ServersWorkspace] add channel agent failed", error);
      toast.error(t("conversationView.toasts.agentAddFailed"));
      throw error;
    }
  };

  const handleRestartAgent = async (agentId: string) => {
    if (!selectedServerId) {
      return;
    }
    const wasStopped =
      (serverAgents.find((agent) => agent.id === agentId)?.lifecycleState || "")
        .trim()
        .toLowerCase() === "inactive";
    try {
      await serversApi.restartAgent(selectedServerId, agentId);
      await refreshMembership(selectedServerId);
      if (activeChannelId) {
        const nextAgents = await serversApi.listChannelAgents(
          selectedServerId,
          activeChannelId,
        );
        setChannelAgents(nextAgents);
        setChannelAgentsByChannelId((current) => ({
          ...current,
          [activeChannelId]: nextAgents,
        }));
      }
      toast.success(
        t(
          wasStopped
            ? "conversationView.toasts.agentStarted"
            : "conversationView.toasts.agentRestarted",
        ),
      );
    } catch (error) {
      console.error("[ServersWorkspace] restart agent failed", error);
      toast.error(t("conversationView.toasts.agentRestartFailed"));
    }
  };

  const handleStopAgent = async (agentId: string) => {
    if (!selectedServerId) {
      return;
    }
    try {
      await serversApi.stopAgent(selectedServerId, agentId);
      await refreshMembership(selectedServerId);
      if (activeChannelId) {
        const nextAgents = await serversApi.listChannelAgents(
          selectedServerId,
          activeChannelId,
        );
        setChannelAgents(nextAgents);
        setChannelAgentsByChannelId((current) => ({
          ...current,
          [activeChannelId]: nextAgents,
        }));
      }
      toast.success(t("conversationView.toasts.agentStopped"));
    } catch (error) {
      console.error("[ServersWorkspace] stop agent failed", error);
      toast.error(t("conversationView.toasts.agentStopFailed"));
    }
  };

  const handlePinAgentRuntime = async (
    agentId: string,
    durationHours: number,
  ) => {
    if (!selectedServerId) {
      return;
    }
    try {
      await serversApi.pinAgentRuntime(
        selectedServerId,
        agentId,
        durationHours,
      );
      await refreshMembership(selectedServerId);
      if (activeChannelId) {
        const nextAgents = await serversApi.listChannelAgents(
          selectedServerId,
          activeChannelId,
        );
        setChannelAgents(nextAgents);
        setChannelAgentsByChannelId((current) => ({
          ...current,
          [activeChannelId]: nextAgents,
        }));
      }
      toast.success(t("runtime.toasts.pinUpdated"));
    } catch (error) {
      console.error("[ServersWorkspace] pin agent runtime failed", error);
      toast.error(t("runtime.toasts.pinUpdateFailed"));
      throw error;
    }
  };

  const handleUnpinAgentRuntime = async (agentId: string) => {
    if (!selectedServerId) {
      return;
    }
    try {
      await serversApi.unpinAgentRuntime(selectedServerId, agentId);
      await refreshMembership(selectedServerId);
      if (activeChannelId) {
        const nextAgents = await serversApi.listChannelAgents(
          selectedServerId,
          activeChannelId,
        );
        setChannelAgents(nextAgents);
        setChannelAgentsByChannelId((current) => ({
          ...current,
          [activeChannelId]: nextAgents,
        }));
      }
      toast.success(t("runtime.toasts.unpinned"));
    } catch (error) {
      console.error("[ServersWorkspace] unpin agent runtime failed", error);
      toast.error(t("runtime.toasts.unpinFailed"));
      throw error;
    }
  };

  const handleRemoveServerAgent = async (agentId: string) => {
    if (!selectedServerId) {
      return;
    }
    try {
      await serversApi.removeAgent(selectedServerId, agentId);
      await refreshMembership(selectedServerId);
      setChannelAgents((current) =>
        current.filter((agent) => agent.id !== agentId),
      );
      setChannelAgentsByChannelId((current) =>
        Object.fromEntries(
          Object.entries(current).map(([currentChannelId, agents]) => [
            currentChannelId,
            agents.filter((agent) => agent.id !== agentId),
          ]),
        ),
      );
      setDrawer({ type: "colleague", selection: null });
      toast.success(t("conversationView.toasts.agentRemoved"));
    } catch (error) {
      console.error("[ServersWorkspace] remove server agent failed", error);
      toast.error(t("conversationView.toasts.agentRemoveFailed"));
    }
  };

  const handleRemoveChannelAgent = async (agentId: string) => {
    if (!selectedServerId || !activeChannelId) {
      return;
    }
    try {
      await serversApi.removeAgentFromChannel(
        selectedServerId,
        activeChannelId,
        agentId,
      );
      setChannelAgents((current) =>
        current.filter((agent) => agent.id !== agentId),
      );
      setChannelAgentsByChannelId((current) => ({
        ...current,
        [activeChannelId]: (current[activeChannelId] ?? []).filter(
          (agent) => agent.id !== agentId,
        ),
      }));
      toast.success(t("conversationView.toasts.agentRemovedFromChannel"));
    } catch (error) {
      console.error("[ServersWorkspace] remove channel agent failed", error);
      toast.error(t("conversationView.toasts.agentRemoveFromChannelFailed"));
    }
  };

  const handleRemoveChannelMember = async (membershipId: number) => {
    if (!selectedServerId || !activeChannelId) {
      return;
    }
    try {
      await serversApi.removeChannelMember(
        selectedServerId,
        activeChannelId,
        membershipId,
      );
      setChannelMembers((current) =>
        current.filter((member) => member.id !== membershipId),
      );
      toast.success(t("conversationView.toasts.memberRemovedFromChannel"));
    } catch (error) {
      console.error("[ServersWorkspace] remove channel member failed", error);
      toast.error(t("conversationView.toasts.memberRemoveFromChannelFailed"));
    }
  };

  const handleMobileBack = () => {
    setIsMobileDetailVisible(false);
    setDrawer({ type: "none" });
    setMode("search");
    const params = new URLSearchParams();
    if (selectedServerId) {
      params.set("server", selectedServerId);
    }
    router.replace(
      `/${lng}/servers${params.toString() ? `?${params.toString()}` : ""}`,
      { scroll: false },
    );
  };

  React.useEffect(() => {
    if (!hasDesktopDrawer) {
      isResizingDrawerRef.current = false;
    }
  }, [hasDesktopDrawer]);

  React.useEffect(() => {
    const onPointerMove = (event: PointerEvent) => {
      if (!isResizingDrawerRef.current || !contentAreaRef.current) {
        return;
      }

      const rect = contentAreaRef.current.getBoundingClientRect();
      const nextDrawerWidth = rect.right - event.clientX;
      const nextRatio = (nextDrawerWidth / rect.width) * 100;
      const clamped = Math.min(70, Math.max(30, nextRatio));
      setDesktopDrawerRatio(clamped);
    };

    const onPointerUp = () => {
      isResizingDrawerRef.current = false;
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };
  }, []);

  const mobileDetailTitle =
    mode === "conversation"
      ? (selectedChannel?.name ?? t("conversationView.loading"))
      : mode === "tasks"
        ? t("conversationView.tasksTab")
        : mode === "colleagues"
          ? t("conversationView.colleaguesTab")
          : mode === "inbox"
            ? t("conversationView.inbox")
            : t("conversationView.searchInServer");

  const sidebarProps = {
    servers,
    selectedServerId,
    mode,
    inboxCount: unreadInboxItems.length,
    topLevelChannels,
    directMessages,
    activeChannelId,
    onSelectServer: switchServer,
    onOpenServerAccess: () => setServerAccessOpen(true),
    onOpenMode: openMode,
    onOpenTasks: openTaskMode,
    onOpenChannel: openChannel,
    onCreateChannel: () => setCreateChannelOpen(true),
  };

  return (
    <main className="relative flex h-[calc(100vh-4rem)] min-h-0 min-w-0 flex-1 overflow-hidden border-t border-border bg-background">
      <ServerWorkspaceSidebar {...sidebarProps} />

      {!isMobileDetailVisible ? (
        <div className="flex min-h-0 flex-1 flex-col md:hidden">
          <ServerWorkspaceSidebar {...sidebarProps} variant="mobile" />
        </div>
      ) : null}

      <div
        className={cn(
          "min-h-0 min-w-0 flex-1 flex-col overflow-hidden md:flex",
          isMobileDetailVisible ? "flex" : "hidden",
        )}
      >
        {showMobileBack ? (
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-card px-4">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="shrink-0 text-muted-foreground"
              aria-label={t("conversationView.mobile.back")}
              title={t("conversationView.mobile.back")}
              onClick={handleMobileBack}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-lg font-semibold text-foreground">
                {mobileDetailTitle}
              </h1>
              {selectedServer ? (
                <p className="truncate text-sm text-muted-foreground">
                  {selectedServer.name}
                </p>
              ) : null}
            </div>
            {showMobileChannelActions ? (
              <ChannelActionButtons
                channel={selectedChannel}
                memberCount={channelMembers.length + channelAgents.length}
                compact
                className="-mr-1 gap-1.5"
                onOpenSettings={() => setSettingsOpen(true)}
                onOpenMembers={() => setMembersOpen(true)}
                onOpenArtifacts={() => setDrawer({ type: "artifacts" })}
                onOpenLeaveConfirm={() => setLeaveChannelOpen(true)}
              />
            ) : null}
          </header>
        ) : null}

        <div
          ref={contentAreaRef}
          className="flex min-h-0 min-w-0 flex-1 overflow-hidden"
          style={
            hasDesktopDrawer
              ? ({
                  "--server-drawer-width": `${desktopDrawerRatio}%`,
                } as React.CSSProperties)
              : undefined
          }
        >
          <div
            className={cn(
              "flex min-h-0 min-w-0 flex-1 flex-col",
              hasDesktopDrawer &&
                "xl:flex-none xl:w-[calc(100%_-_var(--server-drawer-width)_-_0.25rem)]",
            )}
          >
            {feedModeActive ? (
              <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
                {mode === "search" ? (
                  <SearchPanel
                    search={searchValue}
                    onSearchChange={setSearchValue}
                    items={filteredSearchItems}
                    savedMessageIds={savedMessageIds}
                    currentUserId={profile?.id}
                    onOpenThread={(item) => {
                      markMessagesRead([item.message.id]);
                      return setDrawer({
                        type: "thread",
                        channelId: item.channel.id,
                        rootMessageId:
                          item.message.threadRootMessageId ?? item.message.id,
                      });
                    }}
                    onOpenExecution={(sessionId) => {
                      const matchedItem = filteredSearchItems.find(
                        (item) =>
                          item.message.content.source === "agent_execution" &&
                          item.message.content.session_id === sessionId,
                      );
                      if (matchedItem) {
                        markMessagesRead([matchedItem.message.id]);
                      }
                      setDrawer({ type: "execution", sessionId });
                    }}
                    onToggleSaved={toggleSaved}
                    onToggleReaction={(item, emoji) =>
                      void handleToggleReaction(item.message, emoji)
                    }
                  />
                ) : (
                  <FeedPanel
                    inboxItems={inboxItems}
                    savedItems={savedItems}
                    savedMessageIds={savedMessageIds}
                    readMessageIds={readMessageIds}
                    currentUserId={profile?.id}
                    onOpenThread={(item) => {
                      markMessagesRead([item.message.id]);
                      return setDrawer({
                        type: "thread",
                        channelId: item.channel.id,
                        rootMessageId:
                          item.message.threadRootMessageId ?? item.message.id,
                      });
                    }}
                    onOpenExecution={(sessionId) => {
                      const matchedItem = inboxItems.find(
                        (item) =>
                          item.message.content.source === "agent_execution" &&
                          item.message.content.session_id === sessionId,
                      );
                      if (matchedItem) {
                        markMessagesRead([matchedItem.message.id]);
                      }
                      setDrawer({ type: "execution", sessionId });
                    }}
                    onToggleSaved={toggleSaved}
                    onToggleReaction={(item, emoji) =>
                      void handleToggleReaction(item.message, emoji)
                    }
                  />
                )}
              </section>
            ) : colleaguesModeActive ? (
              <ColleaguesPanel
                agents={colleagueDirectoryAgents}
                presets={presets}
                members={serverMembers}
                selection={colleagueSelection}
                activeChannelIdByAgentId={activeChannelIdByAgentId}
                canCreateAgent={canManageServerOps}
                canInviteMembers={canManageServerOps}
                onSelect={(selection) => {
                  setDrawer({ type: "colleague", selection });
                }}
                onOpenActiveChannel={openChannelById}
                onAddAgent={() => setAgentPresetOpen(true)}
                onInviteMember={() => setServerAccessOpen(true)}
              />
            ) : tasksModeActive ? (
              <ChannelTasksWorkspace
                tasks={tasks}
                taskView={taskView}
                activeChannelId={activeChannelId}
                topLevelChannels={topLevelChannels}
                members={channelMembers}
                agents={channelAgents}
                presets={presets}
                canUpdateAssignee={canManageServerOps}
                canUpdateStatus={canManageServerOps}
                onSelectChannel={(value) => {
                  router.push(
                    `/${lng}/servers/${selectedServerId}/channels/${value}?tab=chat&mode=tasks&view=${taskView}`,
                  );
                }}
                onUpdateView={updateTaskView}
                onOpenTask={openTaskThread}
                onUpdateAssignee={updateTaskAssignee}
                onUpdateStatus={updateTaskStatus}
              />
            ) : (
              <ConversationContent
                channel={selectedChannel}
                agents={channelAgents}
                presets={presets}
                members={channelMembers}
                messages={currentMessages}
                savedMessageIds={savedMessageIds}
                draft={draft}
                draftReferences={draftReferences}
                asTask={asTask}
                isLoading={isLoading}
                isUploading={isUploadingDraftFile}
                onDraftChange={setDraft}
                onDraftReferencesChange={setDraftReferences}
                onAsTaskChange={setAsTask}
                onSend={() => void handleSend()}
                onUploadFiles={uploadDraftFiles}
                onOpenThread={(message) =>
                  setDrawer({
                    type: "thread",
                    channelId: activeChannelId!,
                    rootMessageId: message.id,
                  })
                }
                onOpenSettings={() => setSettingsOpen(true)}
                onOpenMembers={() => setMembersOpen(true)}
                onOpenArtifacts={() => setDrawer({ type: "artifacts" })}
                onOpenLeaveConfirm={() => setLeaveChannelOpen(true)}
                onToggleSaved={toggleSaved}
                onToggleReaction={(message, emoji) =>
                  void handleToggleReaction(message, emoji)
                }
                onOpenExecution={(sessionId) =>
                  setDrawer({ type: "execution", sessionId })
                }
                onOpenAgentProfile={(agentId) => {
                  setDrawer({
                    type: "colleague",
                    selection: { kind: "agent", id: agentId },
                  });
                }}
                isSending={isSending}
                currentUserId={profile?.id}
              />
            )}
          </div>

          {hasDesktopDrawer ? (
            <>
              <div
                className="hidden xl:block xl:w-1 xl:shrink-0 xl:cursor-col-resize xl:bg-border/60 xl:hover:bg-primary/40"
                onPointerDown={(event) => {
                  event.preventDefault();
                  isResizingDrawerRef.current = true;
                }}
              />
              <div className="min-w-0 xl:flex xl:h-full xl:flex-none xl:w-[var(--server-drawer-width)]">
                {drawer.type === "thread" ? (
                  <ThreadDrawer
                    thread={threadMessages}
                    serverId={selectedServerId}
                    channelId={drawer.channelId}
                    agents={channelAgents}
                    presets={presets}
                    members={channelMembers}
                    currentUserId={profile?.id}
                    draft={threadDraft}
                    draftReferences={threadDraftReferences}
                    suggestedMentionHandle={threadMentionHandle}
                    asTask={threadAsTask}
                    onDraftChange={setThreadDraft}
                    onDraftReferencesChange={setThreadDraftReferences}
                    onAsTaskChange={setThreadAsTask}
                    onSend={() => void handleReply()}
                    onUploadFiles={uploadThreadDraftFiles}
                    onClose={() => setDrawer({ type: "none" })}
                    onOpenExecution={(sessionId) =>
                      setDrawer({ type: "execution", sessionId })
                    }
                    onToggleReaction={(message, emoji) =>
                      void handleToggleReaction(message, emoji)
                    }
                    isSending={isSending}
                  />
                ) : drawer.type === "execution" ? (
                  <ExecutionDrawer
                    sessionId={drawer.sessionId}
                    onClose={() => setDrawer({ type: "none" })}
                  />
                ) : drawer.type === "agent" ? (
                  <AgentDrawer
                    agents={channelAgents}
                    presets={presets}
                    selectedAgentId={drawer.agentId}
                    canInspectPersistentFiles={
                      selectedServer?.ownerUserId === profile?.id
                    }
                    onSelectAgent={(id) =>
                      setDrawer({ type: "agent", agentId: id })
                    }
                    onClose={() => setDrawer({ type: "none" })}
                    onOpenDm={handleOpenDm}
                  />
                ) : drawer.type === "artifacts" ? (
                  <SharedArtifactsDrawer
                    files={channelArtifacts}
                    isLoading={isLoading}
                    onClose={() => setDrawer({ type: "none" })}
                    onDeleteFile={deleteSharedArtifact}
                    fileListLayoutClassName="xl:grid-cols-[minmax(0,1fr)_minmax(10rem,12rem)]"
                  />
                ) : drawer.type === "colleague" ? (
                  <ColleagueDetail
                    selection={colleagueSelection}
                    agents={
                      colleaguesModeActive
                        ? colleagueDirectoryAgents
                        : knownAgents
                    }
                    presets={presets}
                    members={serverMembers}
                    serverId={selectedServerId}
                    serverKind={selectedServer?.kind}
                    canInspectPersistentFiles={
                      selectedServer?.ownerUserId === profile?.id
                    }
                    currentUserId={profile?.id}
                    currentServerRole={currentServerRole}
                    canManageServerOperations={canManageServerOps}
                    canManageServerMembers={canManageServerMemberRoles}
                    activeChannelId={activeChannelId}
                    channelMembers={channelMembers}
                    activeChannelIdByAgentId={activeChannelIdByAgentId}
                    channelNamesByAgentId={channelNamesByAgentId}
                    onClose={() => {
                      setDrawer({ type: "none" });
                    }}
                    onOpenDm={handleOpenDm}
                    onOpenActiveChannel={openChannelById}
                    onUpdateMemberRole={(membershipId, role) =>
                      updateMemberRole(membershipId, role)
                    }
                    onTransferOwnership={(userId) => transferOwnership(userId)}
                    onRemoveMember={(membershipId) =>
                      void removeMember(membershipId)
                    }
                    onRestartAgent={(agentId) =>
                      void handleRestartAgent(agentId)
                    }
                    onStopAgent={(agentId) => void handleStopAgent(agentId)}
                    onPinAgentRuntime={(agentId, durationHours) =>
                      handlePinAgentRuntime(agentId, durationHours)
                    }
                    onUnpinAgentRuntime={(agentId) =>
                      handleUnpinAgentRuntime(agentId)
                    }
                    onUpdateAgentDescription={updateAgentDescription}
                    onRemoveAgentFromServer={(agentId) =>
                      void handleRemoveServerAgent(agentId)
                    }
                    onRemoveMemberFromChannel={(membershipId) =>
                      void handleRemoveChannelMember(membershipId)
                    }
                  />
                ) : null}
              </div>
            </>
          ) : null}
        </div>
      </div>

      <CreateChannelDialog
        open={createChannelOpen}
        agents={serverAgents}
        members={serverMembers}
        currentUserId={profile?.id}
        onOpenChange={setCreateChannelOpen}
        onCreate={handleCreateChannel}
      />
      <AlertDialog open={leaveChannelOpen} onOpenChange={setLeaveChannelOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t(
                isChannelOwner
                  ? "conversationView.leaveConfirm.ownerTitle"
                  : "conversationView.leaveConfirm.title",
              )}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                isChannelOwner
                  ? "conversationView.leaveConfirm.ownerDescription"
                  : "conversationView.leaveConfirm.description",
                { channel: selectedChannel?.name ?? "" },
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLeavingChannel}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleLeaveChannel()}
              disabled={isLeavingChannel || !selectedChannel}
            >
              {t(
                isChannelOwner
                  ? "conversationView.leaveConfirm.dissolve"
                  : "conversationView.leaveConfirm.leave",
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <ChannelSettingsDialog
        open={settingsOpen}
        channel={selectedChannel}
        isArchiving={isArchivingChannel}
        onOpenChange={setSettingsOpen}
        onSave={(input) => void handleUpdateChannel(input)}
        onArchive={() => void handleArchiveChannel()}
        onDelete={() => void handleDeleteChannel()}
      />
      <ChannelMembersDialog
        open={membersOpen}
        channel={selectedChannel}
        agents={channelAgents}
        availableAgents={availableChannelAgents}
        availableHumans={availableChannelHumans}
        humans={channelMembers}
        canManageMembers={canManageServerOps}
        onOpenChange={setMembersOpen}
        onOpenDm={(agentId) => {
          setMembersOpen(false);
          void handleOpenDm(agentId);
        }}
        onAddAgents={(agentIds) => handleAddChannelAgents(agentIds)}
        onAddMembers={(userIds) => handleAddChannelMembers(userIds)}
        onRemoveAgent={(agentId) => void handleRemoveChannelAgent(agentId)}
        onRemoveMember={(membershipId) =>
          void handleRemoveChannelMember(membershipId)
        }
      />
      <ServerAccessDialog
        open={serverAccessOpen}
        server={selectedServer}
        invites={serverInvites}
        isWorking={isServerAccessWorking}
        canCreateInvite={canManageServerOps}
        onOpenChange={setServerAccessOpen}
        onCreateServer={(name) => void createServer(name)}
        onAcceptInvite={(token) => void acceptInvite(token)}
        onCreateInvite={() => void createInvite()}
        onCopyInvite={(token) => void copyInvite(token)}
      />
      <AgentPresetDialog
        open={agentPresetOpen}
        presets={presets}
        existingAgents={serverAgents}
        isWorking={isAgentCreating}
        onOpenChange={setAgentPresetOpen}
        onCreateAgent={(input) => void createAgent(input)}
      />
    </main>
  );
}
