import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { sendMessageAction } from "@/features/chat/actions/session-actions";
import {
  getMessageAttachmentsAction,
  getMessagesBaseAction,
  getRunsBySessionAction,
} from "@/features/chat/actions/query-actions";
import type {
  ChatMessage,
  ExecutionSession,
  InputFile,
  UsageResponse,
} from "@/features/chat/types";

interface UseChatMessagesOptions {
  session: ExecutionSession | null;
  pollingInterval?: number;
}

interface UseChatMessagesReturn {
  messages: ChatMessage[];
  displayMessages: ChatMessage[];
  isLoadingHistory: boolean;
  isTyping: boolean;
  showTypingIndicator: boolean;
  sendMessage: (content: string, attachments?: InputFile[]) => Promise<void>;
  beginOptimisticRegenerate: (assistantMessageId: number) => string;
  beginOptimisticEditMessage: (args: {
    userMessageId: number;
    content: string;
  }) => string;
  commitOptimisticHistoryMutation: (mutationToken: string) => void;
  rollbackOptimisticHistoryMutation: (mutationToken: string) => void;
  runUsageByUserMessageId: Record<string, UsageResponse | null>;
}

type HistoryMutation =
  | {
      kind: "regenerate";
      assistantMessageId: number;
    }
  | {
      kind: "edit";
      userMessageId: number;
      content: string;
    };

function getNumericMessageId(messageId: string): number | null {
  if (!/^\d+$/.test(messageId)) {
    return null;
  }
  const parsed = Number(messageId);
  return Number.isInteger(parsed) ? parsed : null;
}

function applyHistoryMutation(
  input: ChatMessage[],
  mutation: HistoryMutation | null,
): ChatMessage[] {
  if (!mutation) return input;

  const trimmed = input.filter((message) => {
    // Optimistic-only messages should not survive across history rewrites.
    if (message.id.startsWith("msg-")) {
      return false;
    }

    const messageId = getNumericMessageId(message.id);
    if (messageId === null) {
      return true;
    }

    if (mutation.kind === "regenerate") {
      return messageId < mutation.assistantMessageId;
    }
    return messageId <= mutation.userMessageId;
  });

  if (mutation.kind !== "edit") {
    return trimmed;
  }

  return trimmed.map((message) => {
    const messageId = getNumericMessageId(message.id);
    if (
      messageId !== mutation.userMessageId ||
      message.role !== "user" ||
      message.content === mutation.content
    ) {
      return message;
    }
    return {
      ...message,
      content: mutation.content,
    };
  });
}

function compareMessagesForRenderOrder(a: ChatMessage, b: ChatMessage): number {
  const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
  const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
  if (timeA !== timeB) {
    return timeA - timeB;
  }

  const idA = getNumericMessageId(a.id);
  const idB = getNumericMessageId(b.id);
  if (idA !== null && idB !== null) {
    return idA - idB;
  }
  if (idA !== null) return -1;
  if (idB !== null) return 1;
  return a.id.localeCompare(b.id);
}

/**
 * Manages chat message loading, polling, and optimistic updates
 *
 * Responsibilities:
 * - Load message history when session changes
 * - Poll for new messages during active sessions
 * - Merge local optimistic messages with server messages
 * - Calculate display messages with streaming status
 * - Handle typing indicator state
 */
export function useChatMessages({
  session,
  pollingInterval = Number(process.env.NEXT_PUBLIC_MESSAGE_POLLING_INTERVAL) ||
    3000,
}: UseChatMessagesOptions): UseChatMessagesReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [runUsageByUserMessageId, setRunUsageByUserMessageId] = useState<
    Record<string, UsageResponse | null>
  >({});

  const lastLoadedSessionIdRef = useRef<string | null>(null);
  const realUserMessageIdsRef = useRef<number[] | null>(null);
  const [activeHistoryMutation, setActiveHistoryMutation] =
    useState<HistoryMutation | null>(null);
  const mutationRollbackMessagesRef = useRef<ChatMessage[] | null>(null);
  const activeMutationTokenRef = useRef<string | null>(null);
  const mutationSequenceRef = useRef(0);

  const refreshRealUserMessageIds = useCallback(async () => {
    if (!session?.session_id) return;
    try {
      const runs = await getRunsBySessionAction({
        sessionId: session.session_id,
      });
      const ids = runs
        .map((r) => r.user_message_id)
        .filter((id): id is number => typeof id === "number" && id > 0);

      realUserMessageIdsRef.current = ids;
      const usageByMessageId: Record<string, UsageResponse | null> = {};
      runs.forEach((r) => {
        const key = String(r.user_message_id);
        usageByMessageId[key] = r.usage ?? null;
      });
      setRunUsageByUserMessageId(usageByMessageId);
    } catch (error) {
      console.error("[Chat] Failed to load runs:", error);
      // Keep as null so message rendering falls back to showing all user messages.
      realUserMessageIdsRef.current = null;
      setRunUsageByUserMessageId({});
    }
  }, [session?.session_id]);

  const fetchMessagesWithFilter = useCallback(async (sessionId: string) => {
    const realUserMessageIds = realUserMessageIdsRef.current ?? undefined;
    return getMessagesBaseAction({
      sessionId,
      realUserMessageIds,
    });
  }, []);

  const fetchMessageAttachments = useCallback(async (sessionId: string) => {
    return getMessageAttachmentsAction({ sessionId });
  }, []);

  const applyActiveHistoryMutation = useCallback(
    (input: ChatMessage[]) =>
      applyHistoryMutation(input, activeHistoryMutation),
    [activeHistoryMutation],
  );

  // Helper to merge new server messages with local optimistic messages
  const mergeMessages = useCallback(
    (currentMessages: ChatMessage[], serverMessages: ChatMessage[]) => {
      const currentById = new Map(currentMessages.map((msg) => [msg.id, msg]));
      const finalMessages = serverMessages.map((serverMsg) => {
        const existing = currentById.get(serverMsg.id);
        if (!existing || (existing.attachments?.length ?? 0) === 0) {
          return serverMsg;
        }
        if ((serverMsg.attachments?.length ?? 0) > 0) {
          return serverMsg;
        }
        return {
          ...serverMsg,
          attachments: existing.attachments,
        };
      });

      // Append local optimistic messages that haven't been synced yet
      currentMessages.forEach((localMsg) => {
        // Only care about optimistic messages (id starts with "msg-")
        if (!localMsg.id.startsWith("msg-")) return;

        // Check if this optimistic message is already present in server messages
        const isSynced = serverMessages.some((serverMsg) => {
          if (
            serverMsg.role !== localMsg.role ||
            serverMsg.content !== localMsg.content
          ) {
            return false;
          }

          // Timestamp check - allow 10s skew/lag
          const localTime = localMsg.timestamp
            ? new Date(localMsg.timestamp).getTime()
            : Date.now();
          const serverTime = serverMsg.timestamp
            ? new Date(serverMsg.timestamp).getTime()
            : 0;

          return serverTime >= localTime - 10000;
        });

        if (!isSynced) {
          finalMessages.push(localMsg);
        }
      });

      // Sort by timestamp
      return finalMessages.sort(compareMessagesForRenderOrder);
    },
    [],
  );

  const mergeMessageAttachments = useCallback(
    (
      currentMessages: ChatMessage[],
      attachmentsByMessageId: Record<number, InputFile[]>,
    ) => {
      let hasUpdates = false;
      const updated = currentMessages.map((message) => {
        const messageId = Number(message.id);
        if (!Number.isInteger(messageId)) return message;
        const nextAttachments = attachmentsByMessageId[messageId];
        if (!nextAttachments) return message;

        const currentAttachments = message.attachments ?? [];
        const isSameLength =
          currentAttachments.length === nextAttachments.length;
        const isSame =
          isSameLength &&
          currentAttachments.every((currentFile, index) => {
            const nextFile = nextAttachments[index];
            return (
              currentFile.name === nextFile.name &&
              currentFile.source === nextFile.source &&
              currentFile.size === nextFile.size &&
              currentFile.content_type === nextFile.content_type &&
              currentFile.url === nextFile.url
            );
          });
        if (isSame) return message;

        hasUpdates = true;
        return {
          ...message,
          attachments: nextAttachments,
        };
      });

      return hasUpdates ? updated : currentMessages;
    },
    [],
  );

  // Send message and immediately fetch updated messages
  const sendMessage = useCallback(
    async (content: string, attachments?: InputFile[]) => {
      if (!session?.session_id) return;

      const normalizedContent = content.trim();
      const hasAttachments = (attachments?.length ?? 0) > 0;
      if (!normalizedContent && !hasAttachments) return;

      const sessionId = session.session_id;
      setIsTyping(true);

      // Create a new user message for instant UI update
      const newMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: "user",
        content: normalizedContent,
        status: "sent",
        timestamp: new Date().toISOString(),
        attachments,
      };

      setMessages((prev) => [...prev, newMessage]);

      try {
        await sendMessageAction({
          sessionId,
          content: normalizedContent,
          attachments,
        });

        // Refresh runs so multi-turn conversations only show real user inputs.
        await refreshRealUserMessageIds();

        // Fetch latest messages immediately to confirm sync
        const server = await fetchMessagesWithFilter(sessionId);
        setMessages((prev) =>
          applyActiveHistoryMutation(mergeMessages(prev, server.messages)),
        );
        const attachmentsByMessageId = await fetchMessageAttachments(sessionId);
        setMessages((prev) =>
          applyActiveHistoryMutation(
            mergeMessageAttachments(prev, attachmentsByMessageId),
          ),
        );
      } catch (error) {
        console.error("[Chat] Failed to send message or get reply:", error);
        setIsTyping(false);
      }
    },
    [
      session,
      applyActiveHistoryMutation,
      mergeMessages,
      mergeMessageAttachments,
      refreshRealUserMessageIds,
      fetchMessagesWithFilter,
      fetchMessageAttachments,
    ],
  );

  // Load and poll for messages
  useEffect(() => {
    if (!session?.session_id) return;

    // Only set loading if it's a NEW session
    if (lastLoadedSessionIdRef.current !== session.session_id) {
      setIsLoadingHistory(true);
      setMessages([]);
      setIsTyping(false);
      realUserMessageIdsRef.current = null;
      setActiveHistoryMutation(null);
      mutationRollbackMessagesRef.current = null;
      activeMutationTokenRef.current = null;
      setRunUsageByUserMessageId({});
      lastLoadedSessionIdRef.current = session.session_id;
    }

    let isCancelled = false;

    const fetchMessages = async () => {
      try {
        const history = await fetchMessagesWithFilter(session.session_id);
        if (isCancelled) return;

        setMessages((prev) => {
          // If it's the first load (empty prev), just set it
          // Otherwise merge
          return applyActiveHistoryMutation(
            mergeMessages(prev, history.messages),
          );
        });

        const attachmentsByMessageId = await fetchMessageAttachments(
          session.session_id,
        );
        if (isCancelled) return;
        setMessages((prev) =>
          applyActiveHistoryMutation(
            mergeMessageAttachments(prev, attachmentsByMessageId),
          ),
        );

        if (realUserMessageIdsRef.current === null) {
          void refreshRealUserMessageIds()
            .then(async () => {
              if (isCancelled) return;
              const refreshed = await fetchMessagesWithFilter(
                session.session_id,
              );
              if (isCancelled) return;
              setMessages((prev) =>
                applyActiveHistoryMutation(
                  mergeMessages(prev, refreshed.messages),
                ),
              );
            })
            .catch((error) => {
              console.error(
                "[Chat] Failed to refresh run filters after base message load:",
                error,
              );
            });
        }
      } catch (error) {
        console.error("[Chat] Failed to load messages:", error);
      } finally {
        if (!isCancelled) {
          setIsLoadingHistory(false);
        }
      }
    };

    // Initial fetch
    fetchMessages();

    // Setup polling
    let interval: NodeJS.Timeout;

    const isTerminal = ["completed", "failed", "canceled"].includes(
      session.status,
    );

    if (session.session_id && !isTerminal) {
      interval = setInterval(fetchMessages, pollingInterval);
    } else if (session.session_id && isTerminal) {
      // Refresh run usage once the session becomes terminal so UI can display cost/tokens.
      void refreshRealUserMessageIds();
    }

    return () => {
      isCancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [
    session?.session_id,
    session?.status,
    applyActiveHistoryMutation,
    mergeMessages,
    mergeMessageAttachments,
    pollingInterval,
    fetchMessagesWithFilter,
    fetchMessageAttachments,
    refreshRealUserMessageIds,
  ]);

  // Manage isTyping state based on messages
  useEffect(() => {
    if (messages.length > 0) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "assistant" || lastMsg.role === "system") {
        setIsTyping(false);
      }
    }
  }, [messages]);

  // Determine if session is running/active
  const isSessionActive =
    session?.status === "running" || session?.status === "pending";

  // Reset typing state when session becomes inactive
  useEffect(() => {
    if (!isSessionActive) {
      setIsTyping(false);
    }
  }, [isSessionActive]);

  // Calculate messages for display
  const displayMessages = useMemo(() => {
    if (!isSessionActive || messages.length === 0) return messages;

    const lastMsg = messages[messages.length - 1];
    if (lastMsg.role === "assistant") {
      // Show streaming status if assistant is last message and session is running
      return [
        ...messages.slice(0, -1),
        { ...lastMsg, status: "streaming" as const },
      ];
    }
    return messages;
  }, [messages, isSessionActive]);

  // Determine if we should show the typing indicator
  const showTypingIndicator =
    isTyping ||
    (isSessionActive &&
      (messages.length === 0 || messages[messages.length - 1].role === "user"));

  const beginOptimisticHistoryMutation = useCallback(
    (mutation: HistoryMutation) => {
      const token = `history-${Date.now()}-${mutationSequenceRef.current + 1}`;
      mutationSequenceRef.current += 1;
      mutationRollbackMessagesRef.current = messages;
      activeMutationTokenRef.current = token;
      setActiveHistoryMutation(mutation);
      setMessages((prev) => applyHistoryMutation(prev, mutation));
      setIsTyping(true);
      return token;
    },
    [messages],
  );

  const beginOptimisticRegenerate = useCallback(
    (assistantMessageId: number) =>
      beginOptimisticHistoryMutation({
        kind: "regenerate",
        assistantMessageId,
      }),
    [beginOptimisticHistoryMutation],
  );

  const beginOptimisticEditMessage = useCallback(
    ({ userMessageId, content }: { userMessageId: number; content: string }) =>
      beginOptimisticHistoryMutation({
        kind: "edit",
        userMessageId,
        content,
      }),
    [beginOptimisticHistoryMutation],
  );

  const commitOptimisticHistoryMutation = useCallback(
    (mutationToken: string) => {
      if (activeMutationTokenRef.current !== mutationToken) return;
      mutationRollbackMessagesRef.current = null;
      activeMutationTokenRef.current = null;
      setActiveHistoryMutation(null);
    },
    [],
  );

  const rollbackOptimisticHistoryMutation = useCallback(
    (mutationToken: string) => {
      if (activeMutationTokenRef.current !== mutationToken) return;
      const rollbackMessages = mutationRollbackMessagesRef.current;
      if (rollbackMessages) {
        setMessages(rollbackMessages);
      }
      mutationRollbackMessagesRef.current = null;
      activeMutationTokenRef.current = null;
      setActiveHistoryMutation(null);
      setIsTyping(false);
    },
    [],
  );

  return {
    messages,
    displayMessages,
    isLoadingHistory,
    isTyping,
    showTypingIndicator,
    sendMessage,
    beginOptimisticRegenerate,
    beginOptimisticEditMessage,
    commitOptimisticHistoryMutation,
    rollbackOptimisticHistoryMutation,
    runUsageByUserMessageId,
  };
}
