"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Image as ImageIcon,
  Loader2,
  MessageSquare,
  PanelRightClose,
  PanelRightOpen,
  Quote,
} from "lucide-react";
import { ChatMessageList } from "../../chat/chat-message-list";
import { TodoList } from "./todo-list";
import { StatusBar } from "./status-bar";
import { PendingMessageList } from "./pending-message-list";
import { ChatInput, type ChatInputRef } from "./chat-input";
import { UserInputRequestCard } from "./user-input-request-card";
import { PlanApprovalCard } from "./plan-approval-card";
import { EnterPlanModeCard } from "./enter-plan-mode-card";
import { SkillCreationReviewCard } from "./skill-creation-review-card";
import {
  PanelHeader,
  PanelHeaderAction,
} from "@/components/shared/panel-header";
import { useChatMessages } from "./hooks/use-chat-messages";
import { usePendingMessages } from "./hooks/use-pending-messages";
import { useUserInputRequests } from "./hooks/use-user-input-requests";
import { usePendingSkillCreations } from "./hooks/use-pending-skill-creations";
import {
  branchSessionAction,
  cancelSessionAction,
  editMessageAndRegenerateAction,
  regenerateMessageAction,
} from "@/features/chat/actions/session-actions";
import { getFilesAction } from "@/features/chat/actions/query-actions";
import type {
  DeliverableResponse,
  DeliverableVersionResponse,
  ExecutionSession,
  FileNode,
  InputFile,
  StatePatch,
  UserInputRequest,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { toast } from "sonner";
import { useTaskHistoryContext } from "@/features/projects/contexts/task-history-context";
import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";
import { cn } from "@/lib/utils";
import {
  exportConversationImage,
  type ConversationImageExportMode,
} from "./conversation-image-export";
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
  DialogTitle,
} from "@/components/ui/dialog";
import { useLanguage } from "@/hooks/use-language";
import { ModelSelector } from "@/features/chat/components/chat/model-selector";
import { useModelCatalog } from "@/features/chat/hooks/use-model-catalog";
import {
  normalizeModelSelection,
  type ModelSelection,
} from "@/features/chat/lib/model-catalog";
import type { AssistantDeliverableCardData } from "@/features/chat/components/chat/messages/deliverable-card-group";

interface ChatPanelProps {
  session: ExecutionSession | null;
  statePatch?: StatePatch;
  progress?: number;
  currentStep?: string;
  updateSession: (newSession: Partial<ExecutionSession>) => void;
  onIconClick?: () => void;
  onToggleRightPanel?: () => void;
  showRightPanelToggle?: boolean;
  isRightPanelToggleDisabled?: boolean;
  isRightPanelCollapsed?: boolean;
  hideHeader?: boolean;
  deliverables?: DeliverableResponse[];
  versionsByDeliverableId?: Record<string, DeliverableVersionResponse[]>;
  ensureVersionsForDeliverable?: (
    deliverableId: string | null | undefined,
  ) => Promise<DeliverableVersionResponse[]>;
  onOpenDeliverablePreview?: (deliverableId: string, versionId: string) => void;
  onOpenDeliverableProcess?: (deliverableId: string, versionId: string) => void;
}

interface QuoteSelectionState {
  text: string;
  left: number;
  top: number;
  placeAbove: boolean;
}

function formatAsMarkdownQuote(text: string): string {
  return text
    .split(/\r?\n/)
    .map((line) => (line.length > 0 ? `> ${line}` : ">"))
    .join("\n");
}

function getQueuedQueryPreview(
  content: string,
  attachments: InputFile[] | undefined,
  t: (key: string, options?: Record<string, unknown>) => string,
): string | null {
  const trimmedContent = content.trim();
  if (trimmedContent) {
    return trimmedContent;
  }

  if ((attachments?.length ?? 0) > 0) {
    return t("chatPanel.fileAttachment", {
      count: attachments?.length ?? 0,
    });
  }

  return null;
}

function ChatHistorySkeleton() {
  const shimmerDelay = (index: number) => ({
    animationDelay: `${index * 0.08}s`,
  });
  return (
    <div className="flex h-full w-full flex-col gap-4 py-6" aria-busy="true">
      <div className="flex items-start gap-3">
        <SkeletonCircle className="h-8 w-8" style={shimmerDelay(0)} />
        <SkeletonItem className="w-[70%]" style={shimmerDelay(1)} />
      </div>
      <div className="flex items-start justify-end">
        <SkeletonItem className="w-[68%]" style={shimmerDelay(2)} />
      </div>
      <div className="flex items-start gap-3">
        <SkeletonCircle className="h-8 w-8" style={shimmerDelay(3)} />
        <SkeletonItem className="w-[60%]" style={shimmerDelay(4)} />
      </div>
      <div className="flex items-start justify-end">
        <SkeletonItem className="w-[55%]" style={shimmerDelay(5)} />
      </div>
    </div>
  );
}

/**
 * Chat Panel Container Component
 *
 * Responsibilities:
 * - Compose message and pending message hooks
 * - Coordinate between active/idle session states
 * - Render UI layout
 *
 * Delegates to:
 * - useChatMessages: Message loading, polling, display
 * - usePendingMessages: Queue management, auto-send
 * - ChatInput: Input handling
 * - ChatMessageList: Message rendering
 * - TodoList/StatusBar: State display
 */
export function ChatPanel({
  session,
  statePatch,
  progress = 0,
  currentStep,
  updateSession,
  onIconClick,
  onToggleRightPanel,
  showRightPanelToggle = false,
  isRightPanelToggleDisabled = false,
  isRightPanelCollapsed = false,
  hideHeader = false,
  deliverables = [],
  versionsByDeliverableId = {},
  ensureVersionsForDeliverable,
  onOpenDeliverablePreview,
  onOpenDeliverableProcess,
}: ChatPanelProps) {
  const router = useRouter();
  const lng = useLanguage();
  const { t } = useT("translation");
  const { refreshTasks, touchTask } = useTaskHistoryContext();
  const {
    modelConfig,
    modelOptions,
    isLoading: isLoadingModelCatalog,
  } = useModelCatalog({
    enabled: Boolean(session?.session_id),
  });
  const [isCancelling, setIsCancelling] = React.useState(false);
  const [isExportingImage, setIsExportingImage] = React.useState(false);
  const [branchingMessageId, setBranchingMessageId] = React.useState<
    string | null
  >(null);
  const inputRef = React.useRef<ChatInputRef>(null);
  const panelRootRef = React.useRef<HTMLDivElement>(null);
  const conversationRef = React.useRef<HTMLDivElement>(null);
  const quoteButtonRef = React.useRef<HTMLButtonElement>(null);
  const [quoteSelection, setQuoteSelection] =
    React.useState<QuoteSelectionState | null>(null);
  const [draftModelSelection, setDraftModelSelection] =
    React.useState<ModelSelection | null>(null);
  const [fileUrlByPath, setFileUrlByPath] = React.useState<
    Record<string, string | null>
  >({});

  // Message management hook
  const {
    messages,
    displayMessages,
    isLoadingHistory,
    showTypingIndicator,
    sendMessage,
    beginOptimisticRegenerate,
    beginOptimisticEditMessage,
    commitOptimisticHistoryMutation,
    rollbackOptimisticHistoryMutation,
    reloadMessagesSnapshot,
    runUsageByUserMessageId,
  } = useChatMessages({ session });

  React.useEffect(() => {
    if (!ensureVersionsForDeliverable) return;
    for (const deliverable of deliverables) {
      void ensureVersionsForDeliverable(deliverable.id);
    }
  }, [deliverables, ensureVersionsForDeliverable]);

  React.useEffect(() => {
    const currentSessionId = session?.session_id;
    if (!currentSessionId) {
      setFileUrlByPath({});
      return;
    }

    const visit = (nodes: FileNode[], acc: Record<string, string | null>) => {
      for (const node of nodes) {
        const normalizedPath = node.path.replace(/^\/+/, "");
        if (node.type === "file") {
          acc[normalizedPath] = node.url ?? null;
        }
        if (node.children?.length) {
          visit(node.children, acc);
        }
      }
      return acc;
    };

    void getFilesAction({ sessionId: currentSessionId }).then((nodes) => {
      setFileUrlByPath(visit(nodes, {}));
    });
  }, [deliverables, session?.session_id]);

  const deliverablesByUserMessageId = React.useMemo(() => {
    const grouped: Record<string, AssistantDeliverableCardData[]> = {};

    for (const deliverable of deliverables) {
      const versions = versionsByDeliverableId[deliverable.id] ?? [];
      if (versions.length === 0) continue;

      const sortedVersions = [...versions].sort(
        (a, b) => a.version_no - b.version_no,
      );
      const latestVersion = sortedVersions[sortedVersions.length - 1];
      if (!latestVersion?.source_message_id) continue;

      grouped[String(latestVersion.source_message_id)] ??= [];
      grouped[String(latestVersion.source_message_id)].push({
        deliverableId: deliverable.id,
        logicalName: deliverable.logical_name,
        kind: deliverable.kind,
        versions: sortedVersions,
        fileUrlByVersionId: Object.fromEntries(
          sortedVersions.map((version) => [
            version.id,
            fileUrlByPath[version.file_path.replace(/^\/+/, "")] ?? null,
          ]),
        ),
      });
    }

    return grouped;
  }, [deliverables, fileUrlByPath, versionsByDeliverableId]);

  // Pending message queue hook
  const {
    pendingMessages,
    addPendingMessage,
    refreshPendingMessages,
    sendPendingMessage,
    modifyPendingMessage,
    deletePendingMessage,
  } = usePendingMessages({ session });

  // Determine if session is running/active
  const isSessionActive =
    session?.status === "running" || session?.status === "pending";
  const defaultModelId = (modelConfig?.default_model || "").trim();

  const {
    requests: userInputRequests,
    isLoading: isSubmittingUserInput,
    submitAnswer: submitUserInputAnswer,
  } = useUserInputRequests(
    session?.session_id,
    Boolean(session?.session_id) && isSessionActive,
  );
  const {
    activeCreation: pendingSkillCreation,
    isSubmitting: isSubmittingPendingSkillCreation,
    confirmCreation: confirmPendingSkillCreation,
    cancelCreation: cancelPendingSkillCreation,
  } = usePendingSkillCreations(
    session?.session_id,
    Boolean(session?.session_id) && session?.status === "completed",
  );

  const activeUserInput = userInputRequests[0];
  const [stickyUserInput, setStickyUserInput] =
    React.useState<UserInputRequest | null>(null);
  const stickyTimerRef = React.useRef<number | null>(null);
  const activeUserInputExpiresAt = activeUserInput?.expires_at
    ? new Date(activeUserInput.expires_at).getTime()
    : 0;
  const hasActiveUserInput =
    Boolean(activeUserInput) &&
    (activeUserInputExpiresAt ? activeUserInputExpiresAt > Date.now() : true);

  React.useEffect(() => {
    return () => {
      if (stickyTimerRef.current) {
        window.clearTimeout(stickyTimerRef.current);
        stickyTimerRef.current = null;
      }
    };
  }, []);

  React.useEffect(() => {
    setStickyUserInput(null);
    setQuoteSelection(null);
    setDraftModelSelection(null);
    if (stickyTimerRef.current) {
      window.clearTimeout(stickyTimerRef.current);
      stickyTimerRef.current = null;
    }
  }, [session?.session_id]);

  const defaultSelection = React.useMemo(() => {
    const defaultOption = modelOptions.find((option) => option.isDefault);
    return defaultOption
      ? {
          modelId: defaultOption.modelId,
          providerId: defaultOption.providerId,
        }
      : null;
  }, [modelOptions]);

  const persistedModelSelection = React.useMemo(() => {
    const snapshotModelId =
      (session?.config_snapshot?.model || defaultModelId || "").trim() || null;
    const inferredProviderId =
      (session?.config_snapshot?.model_provider_id || "").trim() ||
      modelOptions.find((option) => option.modelId === snapshotModelId)
        ?.providerId ||
      defaultSelection?.providerId ||
      null;
    return normalizeModelSelection({
      modelId: snapshotModelId,
      providerId: inferredProviderId,
    });
  }, [
    defaultModelId,
    defaultSelection?.providerId,
    modelOptions,
    session?.config_snapshot?.model,
    session?.config_snapshot?.model_provider_id,
  ]);

  const selectedModelSelection = React.useMemo(
    () =>
      normalizeModelSelection(draftModelSelection ?? persistedModelSelection),
    [draftModelSelection, persistedModelSelection],
  );
  const selectedModelId = selectedModelSelection.modelId;
  const selectedModelLabel = React.useMemo(() => {
    if (!selectedModelSelection.modelId) {
      return null;
    }
    return (
      modelOptions.find(
        (option) =>
          option.modelId === selectedModelSelection.modelId &&
          (selectedModelSelection.providerId
            ? option.providerId === selectedModelSelection.providerId
            : true),
      )?.displayName || selectedModelSelection.modelId
    );
  }, [
    modelOptions,
    selectedModelSelection.modelId,
    selectedModelSelection.providerId,
  ]);

  React.useEffect(() => {
    if (!draftModelSelection?.modelId) {
      return;
    }
    if (
      draftModelSelection.modelId === persistedModelSelection.modelId &&
      (draftModelSelection.providerId || "") ===
        (persistedModelSelection.providerId || "")
    ) {
      setDraftModelSelection(null);
    }
  }, [draftModelSelection, persistedModelSelection]);

  const handleSelectModel = React.useCallback(
    (selection: ModelSelection | null) => {
      const nextSelection = normalizeModelSelection(
        selection ?? defaultSelection,
      );
      if (!nextSelection.modelId || !defaultSelection?.modelId) {
        return;
      }
      if (
        nextSelection.modelId === persistedModelSelection.modelId &&
        (nextSelection.providerId || "") ===
          (persistedModelSelection.providerId || "")
      ) {
        setDraftModelSelection(null);
        return;
      }
      setDraftModelSelection(nextSelection);
    },
    [defaultSelection, persistedModelSelection],
  );

  const updateQuoteSelection = React.useCallback(() => {
    const container = conversationRef.current;
    if (!container) {
      setQuoteSelection(null);
      return;
    }

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
      setQuoteSelection(null);
      return;
    }

    const selectedText = selection
      .toString()
      .replace(/\u200B/g, "")
      .trim();
    if (!selectedText) {
      setQuoteSelection(null);
      return;
    }

    const range = selection.getRangeAt(0);
    const commonAncestor = range.commonAncestorContainer;
    const ancestorElement =
      commonAncestor.nodeType === Node.ELEMENT_NODE
        ? (commonAncestor as Element)
        : commonAncestor.parentElement;

    if (!ancestorElement || !container.contains(ancestorElement)) {
      setQuoteSelection(null);
      return;
    }

    const rect =
      range.getBoundingClientRect().width > 0
        ? range.getBoundingClientRect()
        : range.getClientRects()[0];
    if (!rect) {
      setQuoteSelection(null);
      return;
    }

    const minLeft = 80;
    const maxLeft = Math.max(window.innerWidth - 80, minLeft);
    const left = Math.min(
      Math.max(rect.left + rect.width / 2, minLeft),
      maxLeft,
    );
    const placeAbove = rect.top > 56;
    setQuoteSelection({
      text: selectedText,
      left,
      top: placeAbove ? rect.top - 6 : rect.bottom + 6,
      placeAbove,
    });
  }, []);

  const handleConversationMouseUp = React.useCallback(() => {
    window.setTimeout(updateQuoteSelection, 0);
  }, [updateQuoteSelection]);

  React.useEffect(() => {
    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) return;
      if (quoteButtonRef.current?.contains(target)) return;
      if (conversationRef.current?.contains(target)) return;
      setQuoteSelection(null);
    };
    const handleViewportChange = () => {
      setQuoteSelection(null);
    };

    document.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("resize", handleViewportChange);
    window.addEventListener("scroll", handleViewportChange, true);

    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("resize", handleViewportChange);
      window.removeEventListener("scroll", handleViewportChange, true);
    };
  }, []);

  React.useEffect(() => {
    if (!session?.session_id) return;
    const hasCountdown =
      Boolean(activeUserInput) &&
      activeUserInput.tool_name !== "ExitPlanMode" &&
      activeUserInputExpiresAt > Date.now();
    touchTask(session.session_id, {
      hasPendingUserInput: hasCountdown,
      bumpToTop: false,
    });
  }, [
    activeUserInput,
    activeUserInputExpiresAt,
    session?.session_id,
    touchTask,
  ]);

  React.useEffect(() => {
    if (!session?.session_id) return;
    const syncedTitle = session.title?.trim();
    if (!syncedTitle) return;

    // Keep sidebar task title in sync with panel subtitle timing.
    touchTask(session.session_id, {
      title: syncedTitle,
      bumpToTop: false,
    });
  }, [session?.session_id, session?.title, touchTask]);

  const isSessionCancelable =
    session?.status === "running" || session?.status === "pending";

  const handleCancel = React.useCallback(async () => {
    if (!session?.session_id) return;
    if (!isSessionCancelable) return;
    if (isCancelling) return;

    const prevStatus = session.status;
    setIsCancelling(true);
    // Optimistically mark as terminal so polling/streaming stops immediately.
    updateSession({ status: "canceled" });

    try {
      await cancelSessionAction({ sessionId: session.session_id });
    } catch (error) {
      console.error("[ChatPanel] Failed to cancel session:", error);
      // Best-effort revert so the UI doesn't get stuck in a wrong terminal state.
      updateSession({ status: prevStatus });
    } finally {
      setIsCancelling(false);
    }
  }, [
    isCancelling,
    isSessionCancelable,
    session?.session_id,
    session?.status,
    updateSession,
  ]);

  const handleSubmitUserInput = React.useCallback(
    async (request: UserInputRequest, answers: Record<string, string>) => {
      setStickyUserInput(request);
      try {
        await submitUserInputAnswer(request.id, answers);
        if (stickyTimerRef.current) {
          window.clearTimeout(stickyTimerRef.current);
        }
        stickyTimerRef.current = window.setTimeout(() => {
          setStickyUserInput(null);
          stickyTimerRef.current = null;
        }, 1500);
      } catch (error) {
        throw error;
      }
    },
    [submitUserInputAnswer],
  );

  const userPromptHistory = React.useMemo(
    () =>
      messages
        .filter(
          (message) =>
            message.role === "user" && typeof message.content === "string",
        )
        .map((message) => (message.content as string).trim())
        .filter((content) => content.length > 0),
    [messages],
  );

  const handleEditMessage = React.useCallback(
    ({
      messageId,
      content,
    }: {
      messageId: string;
      content: string;
    }): Promise<void> => {
      if (!session?.session_id) return Promise.resolve();
      const userMessageId = Number(messageId);
      if (!Number.isInteger(userMessageId) || userMessageId <= 0) {
        toast.error(t("chat.editMessageFailed"));
        return Promise.resolve();
      }
      const trimmedContent = content.trim();
      if (!trimmedContent) {
        toast.error(t("chat.editMessageFailed"));
        return Promise.resolve();
      }

      const previousStatus = session.status;
      const mutationToken = beginOptimisticEditMessage({
        userMessageId,
        content: trimmedContent,
      });
      touchTask(session.session_id, {
        status: "pending",
        timestamp: new Date().toISOString(),
        bumpToTop: true,
      });
      if (session.status !== "running" && session.status !== "pending") {
        updateSession({ status: "pending" });
      }

      void (async () => {
        try {
          await editMessageAndRegenerateAction({
            sessionId: session.session_id,
            userMessageId,
            content: trimmedContent,
            model: selectedModelSelection.modelId ?? undefined,
            model_provider_id: selectedModelSelection.providerId ?? undefined,
          });
          await reloadMessagesSnapshot();
          commitOptimisticHistoryMutation(mutationToken);
          void refreshTasks();
        } catch (error) {
          console.error("[ChatPanel] Failed to edit message:", error);
          rollbackOptimisticHistoryMutation(mutationToken);
          updateSession({ status: previousStatus });
          toast.error(t("chat.editMessageFailed"));
          void refreshTasks();
        }
      })();

      return Promise.resolve();
    },
    [
      beginOptimisticEditMessage,
      commitOptimisticHistoryMutation,
      refreshTasks,
      reloadMessagesSnapshot,
      rollbackOptimisticHistoryMutation,
      selectedModelSelection,
      session?.session_id,
      session?.status,
      t,
      touchTask,
      updateSession,
    ],
  );

  const handleInsertQuote = React.useCallback(() => {
    if (!quoteSelection) return;
    inputRef.current?.appendValueAndFocus(
      formatAsMarkdownQuote(quoteSelection.text),
    );
    setQuoteSelection(null);
    window.getSelection()?.removeAllRanges();
  }, [quoteSelection]);

  // Handle send from input
  const handleSend = React.useCallback(
    async (content: string, attachments?: InputFile[]) => {
      if (!session?.session_id) return;

      if (hasActiveUserInput) {
        return;
      }

      const previousStatus = session.status;
      const shouldMarkSessionPending =
        session.status !== "running" && session.status !== "pending";
      const previousQueueHeadPreview =
        getQueuedQueryPreview(
          pendingMessages[0]?.content ?? "",
          pendingMessages[0]?.attachments,
          t,
        ) ||
        session.next_queued_query_preview ||
        null;
      const nextPreview = getQueuedQueryPreview(content, attachments, t);

      touchTask(session.session_id, {
        status: "pending",
        timestamp: new Date().toISOString(),
        bumpToTop: true,
      });

      if (shouldMarkSessionPending) {
        updateSession({ status: "pending" });
      }

      const result = await sendMessage(
        content,
        attachments,
        selectedModelSelection,
      );

      if (!result) {
        if (shouldMarkSessionPending) {
          updateSession({ status: previousStatus });
        }
        return;
      }

      if (result.acceptedType === "queued_query") {
        addPendingMessage({
          id: result.queueItemId ?? `queued-${Date.now()}`,
          content,
          attachments,
          status: "queued",
        });
      }

      updateSession({
        ...(result.acceptedType === "queued_query"
          ? { status: "pending" as const }
          : {}),
        queued_query_count: result.queuedQueryCount,
        next_queued_query_preview:
          result.queuedQueryCount > 0
            ? (previousQueueHeadPreview ?? nextPreview)
            : null,
      });

      void refreshPendingMessages();
      await refreshTasks();
    },
    [
      addPendingMessage,
      hasActiveUserInput,
      pendingMessages,
      refreshPendingMessages,
      refreshTasks,
      sendMessage,
      selectedModelSelection,
      session?.next_queued_query_preview,
      session?.session_id,
      session?.status,
      t,
      touchTask,
      updateSession,
    ],
  );

  const handleSendPendingMessage = React.useCallback(
    async (messageId: string) => {
      try {
        const result = await sendPendingMessage(messageId);
        if (!result) {
          return;
        }

        const remainingMessages = pendingMessages.filter(
          (message) => message.id !== messageId,
        );

        updateSession({
          status: "pending",
          queued_query_count: result.queuedQueryCount,
          next_queued_query_preview:
            result.queuedQueryCount > 0
              ? getQueuedQueryPreview(
                  remainingMessages[0]?.content ?? "",
                  remainingMessages[0]?.attachments,
                  t,
                )
              : null,
        });

        if (result.acceptedType === "run" && session?.session_id) {
          touchTask(session.session_id, {
            status: "pending",
            timestamp: new Date().toISOString(),
            bumpToTop: true,
          });
        }

        await refreshTasks();
      } catch (error) {
        console.error("[ChatPanel] Failed to send queued query:", error);
        toast.error(t("hero.toasts.actionFailed"));
        await refreshPendingMessages();
      }
    },
    [
      pendingMessages,
      refreshPendingMessages,
      refreshTasks,
      sendPendingMessage,
      session?.session_id,
      t,
      touchTask,
      updateSession,
    ],
  );

  const handleModifyPendingMessage = React.useCallback(
    async (messageId: string) => {
      try {
        const draft = await modifyPendingMessage(messageId);
        if (!draft) {
          return;
        }

        const remainingMessages = pendingMessages.filter(
          (message) => message.id !== messageId,
        );
        updateSession({
          queued_query_count: remainingMessages.length,
          next_queued_query_preview: getQueuedQueryPreview(
            remainingMessages[0]?.content ?? "",
            remainingMessages[0]?.attachments,
            t,
          ),
        });
        inputRef.current?.setDraftAndFocus({
          value: draft.content,
          attachments: draft.attachments,
        });
        await refreshTasks();
      } catch (error) {
        console.error("[ChatPanel] Failed to modify queued query:", error);
        toast.error(t("hero.toasts.actionFailed"));
        await refreshPendingMessages();
      }
    },
    [
      modifyPendingMessage,
      pendingMessages,
      refreshPendingMessages,
      refreshTasks,
      t,
      updateSession,
    ],
  );

  const handleDeletePendingMessage = React.useCallback(
    async (messageId: string) => {
      try {
        await deletePendingMessage(messageId);
        const remainingMessages = pendingMessages.filter(
          (message) => message.id !== messageId,
        );
        updateSession({
          queued_query_count: remainingMessages.length,
          next_queued_query_preview: getQueuedQueryPreview(
            remainingMessages[0]?.content ?? "",
            remainingMessages[0]?.attachments,
            t,
          ),
        });
        await refreshTasks();
      } catch (error) {
        console.error("[ChatPanel] Failed to delete queued query:", error);
        toast.error(t("hero.toasts.actionFailed"));
        await refreshPendingMessages();
      }
    },
    [
      deletePendingMessage,
      pendingMessages,
      refreshPendingMessages,
      refreshTasks,
      t,
      updateSession,
    ],
  );

  const handleRegenerateMessage = React.useCallback(
    ({
      userMessageId,
      assistantMessageId,
    }: {
      userMessageId: string;
      assistantMessageId: string;
    }) => {
      if (!session?.session_id) return;

      const userMessageIdNumber = Number(userMessageId);
      const assistantMessageIdNumber = Number(assistantMessageId);
      if (
        !Number.isInteger(userMessageIdNumber) ||
        userMessageIdNumber <= 0 ||
        !Number.isInteger(assistantMessageIdNumber) ||
        assistantMessageIdNumber <= 0
      ) {
        toast.error(t("chat.regenerateFailed"));
        return;
      }
      const previousStatus = session.status;
      const mutationToken = beginOptimisticRegenerate(assistantMessageIdNumber);
      touchTask(session.session_id, {
        status: "pending",
        timestamp: new Date().toISOString(),
        bumpToTop: true,
      });
      if (session.status !== "running" && session.status !== "pending") {
        updateSession({ status: "pending" });
      }

      void (async () => {
        try {
          await regenerateMessageAction({
            sessionId: session.session_id,
            userMessageId: userMessageIdNumber,
            assistantMessageId: assistantMessageIdNumber,
            model: selectedModelSelection.modelId ?? undefined,
            model_provider_id: selectedModelSelection.providerId ?? undefined,
          });
          await reloadMessagesSnapshot();
          commitOptimisticHistoryMutation(mutationToken);
          void refreshTasks();
        } catch (error) {
          console.error("[ChatPanel] Failed to regenerate message:", error);
          rollbackOptimisticHistoryMutation(mutationToken);
          updateSession({ status: previousStatus });
          toast.error(t("chat.regenerateFailed"));
          void refreshTasks();
        }
      })();
    },
    [
      beginOptimisticRegenerate,
      commitOptimisticHistoryMutation,
      refreshTasks,
      reloadMessagesSnapshot,
      rollbackOptimisticHistoryMutation,
      selectedModelSelection,
      session?.session_id,
      session?.status,
      t,
      touchTask,
      updateSession,
    ],
  );

  const handleCreateBranch = React.useCallback(
    (assistantMessageId: string) => {
      if (!session?.session_id) return;
      if (branchingMessageId) return;

      const messageId = Number(assistantMessageId);
      if (!Number.isInteger(messageId) || messageId <= 0) {
        toast.error(t("chat.branchCreateFailed"));
        return;
      }

      setBranchingMessageId(assistantMessageId);
      const loadingToastId = toast.loading(
        t("chat.branchCreating", "Creating branch..."),
      );

      void (async () => {
        try {
          const branched = await branchSessionAction({
            sessionId: session.session_id,
            messageId,
          });
          toast.success(t("chat.branchCreated"), { id: loadingToastId });
          void refreshTasks();
          router.push(
            lng
              ? `/${lng}/chat/${branched.sessionId}`
              : `/chat/${branched.sessionId}`,
          );
        } catch (error) {
          console.error("[ChatPanel] Failed to branch session:", error);
          toast.error(t("chat.branchCreateFailed"), { id: loadingToastId });
        } finally {
          setBranchingMessageId(null);
        }
      })();
    },
    [branchingMessageId, lng, refreshTasks, router, session?.session_id, t],
  );

  // Condition checks for UI sections
  const hasTodos = statePatch?.todos && statePatch.todos.length > 0;
  // Check for config snapshot or runtime data
  const hasConfigSnapshot =
    session?.config_snapshot &&
    ((session.config_snapshot.mcp_server_ids &&
      session.config_snapshot.mcp_server_ids.length > 0) ||
      session.config_snapshot.browser_enabled === true ||
      (session.config_snapshot.plugin_ids &&
        session.config_snapshot.plugin_ids.length > 0) ||
      (session.config_snapshot.skill_ids &&
        session.config_snapshot.skill_ids.length > 0));
  const hasSkills =
    statePatch?.skills_used && statePatch.skills_used.length > 0;
  const hasMcp = statePatch?.mcp_status && statePatch.mcp_status.length > 0;
  const hasBrowser = Boolean(
    session?.config_snapshot?.browser_enabled || statePatch?.browser?.enabled,
  );
  const headerTitle =
    session?.task_name?.trim() ||
    session?.new_message?.title?.trim() ||
    t("chat.executionTitle");
  const headerDescription = session?.title?.trim() || t("chat.emptyStateDesc");
  const contentPaddingClass = isRightPanelCollapsed ? "px-[20%]" : "px-4";
  const messagePaddingClass = isRightPanelCollapsed ? "px-[20%]" : "px-6";
  const canExportConversationImage =
    !isLoadingHistory &&
    (displayMessages.length > 0 || showTypingIndicator) &&
    Boolean(session?.session_id);
  const queuedMessageCount = Math.max(
    session?.queued_query_count ?? 0,
    pendingMessages.length,
  );

  const handleExportConversationImage = React.useCallback(
    async (mode: ConversationImageExportMode) => {
      if (!canExportConversationImage) return;
      if (isExportingImage) return;
      if (!panelRootRef.current) return;

      setIsExportingImage(true);
      try {
        const result = await exportConversationImage({
          panelElement: panelRootRef.current,
          filename: headerDescription,
          mode,
        });

        if (result.count === 0) {
          toast.error(t("chat.exportImageEmpty"));
          return;
        }

        if (result.mode === "multi") {
          toast.success(
            t("chat.exportImageMultiSuccess", {
              count: result.count,
            }),
          );
        } else {
          toast.success(t("chat.exportImageSuccess"));
        }
      } catch (error) {
        console.error(
          "[ChatPanel] Failed to export conversation image:",
          error,
        );
        toast.error(t("chat.exportImageFailed"));
      } finally {
        setIsExportingImage(false);
      }
    },
    [canExportConversationImage, headerDescription, isExportingImage, t],
  );

  return (
    <div
      ref={panelRootRef}
      className="flex flex-col h-full bg-background min-w-0"
      data-chat-panel-export
    >
      {/* Header */}
      {!hideHeader ? (
        <PanelHeader
          icon={MessageSquare}
          title={headerTitle}
          description={headerDescription}
          onIconClick={onIconClick}
          action={
            session?.session_id || showRightPanelToggle ? (
              <div className="flex items-center gap-1">
                {selectedModelId ? (
                  <ModelSelector
                    options={modelOptions}
                    selection={selectedModelSelection}
                    defaultSelection={defaultSelection}
                    fallbackLabel={selectedModelLabel || selectedModelId}
                    onChange={handleSelectModel}
                    disabled={isLoadingModelCatalog}
                    triggerClassName="h-8 max-w-[220px] px-2"
                  />
                ) : null}
                {session?.session_id ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <PanelHeaderAction
                        title={t("chat.exportImage")}
                        disabled={
                          !canExportConversationImage || isExportingImage
                        }
                      >
                        {isExportingImage ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <ImageIcon className="size-4" />
                        )}
                      </PanelHeaderAction>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={() => handleExportConversationImage("long")}
                        disabled={
                          !canExportConversationImage || isExportingImage
                        }
                      >
                        {t("chat.exportLongImage")}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleExportConversationImage("multi")}
                        disabled={
                          !canExportConversationImage || isExportingImage
                        }
                      >
                        {t("chat.exportMultiImage")}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : null}
                {showRightPanelToggle ? (
                  <PanelHeaderAction
                    onClick={onToggleRightPanel}
                    disabled={isRightPanelToggleDisabled}
                    title={
                      isRightPanelCollapsed
                        ? t("chat.expandRightPanel")
                        : t("chat.collapseRightPanel")
                    }
                  >
                    {isRightPanelCollapsed ? (
                      <PanelRightOpen className="size-4" />
                    ) : (
                      <PanelRightClose className="size-4" />
                    )}
                  </PanelHeaderAction>
                ) : null}
              </div>
            ) : null
          }
        />
      ) : null}

      {/* Top Section: Todo List (full width) */}
      {hasTodos && (
        <div className={cn("pt-4 pb-2 shrink-0", contentPaddingClass)}>
          <TodoList
            todos={statePatch.todos!}
            progress={progress}
            currentStep={currentStep}
          />
        </div>
      )}

      {/* Message list */}
      <div
        ref={conversationRef}
        className="flex-1 min-h-0 min-w-0 overflow-hidden"
        onMouseUp={handleConversationMouseUp}
      >
        {isLoadingHistory ? (
          <div className={cn("h-full", contentPaddingClass)}>
            <ChatHistorySkeleton />
          </div>
        ) : (
          <ChatMessageList
            messages={displayMessages}
            isTyping={showTypingIndicator}
            sessionStatus={session?.status}
            repoUrl={session?.config_snapshot?.repo_url ?? null}
            gitBranch={session?.config_snapshot?.git_branch ?? null}
            runUsageByUserMessageId={runUsageByUserMessageId}
            onEditMessage={handleEditMessage}
            onRegenerateMessage={handleRegenerateMessage}
            onCreateBranch={handleCreateBranch}
            branchingAssistantMessageId={branchingMessageId}
            deliverablesByUserMessageId={deliverablesByUserMessageId}
            onOpenDeliverablePreview={onOpenDeliverablePreview}
            onOpenDeliverableProcess={onOpenDeliverableProcess}
            showUserPromptTimeline={isRightPanelCollapsed}
            contentPaddingClassName={messagePaddingClass}
            scrollButtonClassName={
              isRightPanelCollapsed ? "right-[20%]" : undefined
            }
          />
        )}
      </div>

      {quoteSelection ? (
        <button
          ref={quoteButtonRef}
          type="button"
          onMouseDown={(event) => {
            event.preventDefault();
          }}
          onClick={handleInsertQuote}
          className="fixed z-40 inline-flex items-center gap-1 rounded-md border border-border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md transition-colors hover:bg-accent hover:text-accent-foreground"
          aria-label={t("chat.quoteModify")}
          title={t("chat.quoteModify")}
          style={{
            left: quoteSelection.left,
            top: quoteSelection.top,
            transform: quoteSelection.placeAbove
              ? "translate(-50%, -100%)"
              : "translate(-50%, 0)",
          }}
        >
          <Quote className="size-3" />
          {t("chat.quoteModify")}
        </button>
      ) : null}

      {activeUserInput || stickyUserInput ? (
        <div className={cn("pb-3", contentPaddingClass)}>
          {activeUserInput?.tool_name === "ExitPlanMode" ? (
            <PlanApprovalCard
              request={activeUserInput}
              isSubmitting={isSubmittingUserInput}
              onApprove={() =>
                submitUserInputAnswer(activeUserInput.id, { approved: "true" })
              }
              onReject={() =>
                submitUserInputAnswer(activeUserInput.id, { approved: "false" })
              }
            />
          ) : activeUserInput?.tool_name === "EnterPlanMode" ? (
            <EnterPlanModeCard
              request={activeUserInput}
              isSubmitting={isSubmittingUserInput}
              onConfirm={() =>
                submitUserInputAnswer(activeUserInput.id, { confirmed: "true" })
              }
            />
          ) : activeUserInput || stickyUserInput ? (
            <UserInputRequestCard
              request={activeUserInput ?? stickyUserInput!}
              isSubmitting={isSubmittingUserInput}
              onSubmit={(answers) =>
                handleSubmitUserInput(
                  activeUserInput ?? stickyUserInput!,
                  answers,
                )
              }
            />
          ) : null}
        </div>
      ) : null}

      <Dialog
        open={Boolean(pendingSkillCreation)}
        onOpenChange={() => undefined}
      >
        <DialogContent
          className="max-h-[90vh]   w-[calc(100vw-2rem)] sm:max-w-[90vw]
 lg:max-w-[960px] xl:max-w-[1000px overflow-hidden p-0"
          showCloseButton={false}
        >
          <DialogTitle className="sr-only">
            {t("chat.skillCreationReview.title")}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {t("chat.skillCreationReview.subtitle")}
          </DialogDescription>
          {pendingSkillCreation ? (
            <SkillCreationReviewCard
              creation={pendingSkillCreation}
              isSubmitting={isSubmittingPendingSkillCreation}
              className="border-0 bg-transparent p-6 shadow-none"
              onConfirm={(payload) =>
                confirmPendingSkillCreation(pendingSkillCreation.id, payload)
              }
              onCancel={() =>
                cancelPendingSkillCreation(pendingSkillCreation.id)
              }
            />
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Status Bar - Skills and MCP */}
      {(hasConfigSnapshot || hasSkills || hasMcp || hasBrowser) && (
        <StatusBar
          configSnapshot={session?.config_snapshot}
          skills={statePatch?.skills_used}
          mcpStatuses={statePatch?.mcp_status}
          browser={statePatch?.browser}
          className={isRightPanelCollapsed ? "px-[20%]" : undefined}
        />
      )}

      {/* Pending Messages Queue */}
      {queuedMessageCount > 0 && (
        <PendingMessageList
          messages={pendingMessages}
          queuedCount={session?.queued_query_count}
          onSend={handleSendPendingMessage}
          onModify={handleModifyPendingMessage}
          onDelete={handleDeletePendingMessage}
          className={isRightPanelCollapsed ? "px-[20%]" : undefined}
        />
      )}

      {/* Input */}
      <ChatInput
        ref={inputRef}
        onSend={handleSend}
        onCancel={handleCancel}
        canCancel={isSessionCancelable || isCancelling}
        isCancelling={isCancelling}
        disabled={!session?.session_id || hasActiveUserInput || isCancelling}
        history={userPromptHistory}
        className={isRightPanelCollapsed ? "px-[20%]" : undefined}
      />
    </div>
  );
}
