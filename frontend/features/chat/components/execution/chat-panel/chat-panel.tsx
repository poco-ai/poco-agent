"use client";

import * as React from "react";
import {
  Image as ImageIcon,
  Loader2,
  MessageSquare,
  PanelRightClose,
  PanelRightOpen,
  Pencil,
  Quote,
} from "lucide-react";
import { ChatMessageList } from "../../chat/chat-message-list";
import { TodoList } from "./todo-list";
import { StatusBar } from "./status-bar";
import { PendingMessageList } from "./pending-message-list";
import { ChatInput, type ChatInputRef } from "./chat-input";
import { UserInputRequestCard } from "./user-input-request-card";
import { PlanApprovalCard } from "./plan-approval-card";
import {
  PanelHeader,
  PanelHeaderAction,
} from "@/components/shared/panel-header";
import { useChatMessages } from "./hooks/use-chat-messages";
import { usePendingMessages } from "./hooks/use-pending-messages";
import { useUserInputRequests } from "./hooks/use-user-input-requests";
import {
  cancelSessionAction,
  renameSessionTitleAction,
} from "@/features/chat/actions/session-actions";
import { RenameTaskDialog } from "@/features/projects/components/rename-task-dialog";
import type {
  ExecutionSession,
  StatePatch,
  InputFile,
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

interface ChatPanelProps {
  session: ExecutionSession | null;
  statePatch?: StatePatch;
  progress?: number;
  currentStep?: string;
  updateSession: (newSession: Partial<ExecutionSession>) => void;
  onIconClick?: () => void;
  onToggleRightPanel?: () => void;
  isRightPanelCollapsed?: boolean;
  hideHeader?: boolean;
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
  isRightPanelCollapsed = false,
  hideHeader = false,
}: ChatPanelProps) {
  const { t } = useT("translation");
  const { refreshTasks, touchTask } = useTaskHistoryContext();
  const [isCancelling, setIsCancelling] = React.useState(false);
  const [isExportingImage, setIsExportingImage] = React.useState(false);
  const [isRenameDialogOpen, setIsRenameDialogOpen] = React.useState(false);
  const inputRef = React.useRef<ChatInputRef>(null);
  const panelRootRef = React.useRef<HTMLDivElement>(null);
  const conversationRef = React.useRef<HTMLDivElement>(null);
  const quoteButtonRef = React.useRef<HTMLButtonElement>(null);
  const [quoteSelection, setQuoteSelection] =
    React.useState<QuoteSelectionState | null>(null);

  // Message management hook
  const {
    messages,
    displayMessages,
    isLoadingHistory,
    showTypingIndicator,
    sendMessage,
    runUsageByUserMessageId,
  } = useChatMessages({ session });

  // Pending message queue hook
  const {
    pendingMessages,
    addPendingMessage,
    sendPendingMessage,
    modifyPendingMessage,
    deletePendingMessage,
  } = usePendingMessages({ session, sendMessage });

  // Determine if session is running/active
  const isSessionActive =
    session?.status === "running" || session?.status === "pending";

  const {
    requests: userInputRequests,
    isLoading: isSubmittingUserInput,
    submitAnswer: submitUserInputAnswer,
  } = useUserInputRequests(
    session?.session_id,
    Boolean(session?.session_id) && isSessionActive,
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
    if (stickyTimerRef.current) {
      window.clearTimeout(stickyTimerRef.current);
      stickyTimerRef.current = null;
    }
  }, [session?.session_id]);

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

  const handleRename = React.useCallback(
    async (newTitle: string) => {
      if (!session?.session_id) return;
      try {
        await renameSessionTitleAction({
          sessionId: session.session_id,
          title: newTitle,
        });
        updateSession({ title: newTitle });
        toast.success(t("task.toasts.renamed"));
        await refreshTasks();
      } catch (error) {
        console.error("[ChatPanel] Failed to rename session title:", error);
        toast.error(t("task.toasts.renameFailed"));
      }
    },
    [refreshTasks, session?.session_id, t, updateSession],
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

  // Handle edit message - load content into input
  const handleEditMessage = React.useCallback((content: string) => {
    inputRef.current?.setValueAndFocus(content);
  }, []);

  const handleInsertQuote = React.useCallback(() => {
    if (!quoteSelection) return;
    inputRef.current?.appendValueAndFocus(
      formatAsMarkdownQuote(quoteSelection.text),
    );
    setQuoteSelection(null);
    window.getSelection()?.removeAllRanges();
  }, [quoteSelection]);

  // Handle send from input
  const handleSend = async (content: string, attachments?: InputFile[]) => {
    if (!session?.session_id) return;

    if (hasActiveUserInput) {
      return;
    }

    if (isSessionActive) {
      // Session is running, add to pending queue
      addPendingMessage(content, attachments);
    } else {
      // Optimistically update sidebar task status so it reflects the new turn immediately.
      touchTask(session.session_id, {
        status: "pending",
        timestamp: new Date().toISOString(),
        bumpToTop: true,
      });

      // Session is idle, send immediately and mark as active
      if (session.status !== "running" && session.status !== "pending") {
        updateSession({ status: "pending" });
      }
      await sendMessage(content, attachments);
      // Ensure sidebar converges to backend truth (status/updated_at/title).
      await refreshTasks();
    }
  };

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
            session?.session_id || onToggleRightPanel ? (
              <div className="flex items-center gap-1">
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
                {session?.session_id ? (
                  <PanelHeaderAction
                    onClick={() => setIsRenameDialogOpen(true)}
                    title={t("sidebar.rename")}
                  >
                    <Pencil className="size-4" />
                  </PanelHeaderAction>
                ) : null}
                {onToggleRightPanel ? (
                  <PanelHeaderAction
                    onClick={onToggleRightPanel}
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
      {pendingMessages.length > 0 && (
        <PendingMessageList
          messages={pendingMessages}
          onSend={sendPendingMessage}
          onModify={modifyPendingMessage}
          onDelete={deletePendingMessage}
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

      <RenameTaskDialog
        open={isRenameDialogOpen}
        onOpenChange={setIsRenameDialogOpen}
        taskName={session?.title || ""}
        onRename={handleRename}
      />
    </div>
  );
}
