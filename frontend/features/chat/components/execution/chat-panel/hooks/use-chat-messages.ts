import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { sendMessageAction } from "@/features/chat/actions/session-actions";
import {
  getMessagesAction,
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
  runUsageByUserMessageId: Record<string, UsageResponse | null>;
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

  const fetchMessagesWithFilter = useCallback(
    async (sessionId: string) => {
      // Ensure we have a whitelist of real user input message ids (per run).
      if (realUserMessageIdsRef.current === null) {
        await refreshRealUserMessageIds();
      }

      const realUserMessageIds = realUserMessageIdsRef.current ?? undefined;
      return getMessagesAction({
        sessionId,
        realUserMessageIds,
      });
    },
    [refreshRealUserMessageIds],
  );

  // Helper to merge new server messages with local optimistic messages
  const mergeMessages = useCallback(
    (currentMessages: ChatMessage[], serverMessages: ChatMessage[]) => {
      const finalMessages = [...serverMessages];

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
      return finalMessages.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
        return timeA - timeB;
      });
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
        setMessages((prev) => mergeMessages(prev, server.messages));
      } catch (error) {
        console.error("[Chat] Failed to send message or get reply:", error);
        setIsTyping(false);
      }
    },
    [
      session,
      mergeMessages,
      refreshRealUserMessageIds,
      fetchMessagesWithFilter,
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
      setRunUsageByUserMessageId({});
      lastLoadedSessionIdRef.current = session.session_id;
    }

    const fetchMessages = async () => {
      try {
        const history = await fetchMessagesWithFilter(session.session_id);

        setMessages((prev) => {
          // If it's the first load (empty prev), just set it
          // Otherwise merge
          return mergeMessages(prev, history.messages);
        });
      } catch (error) {
        console.error("[Chat] Failed to load messages:", error);
      } finally {
        setIsLoadingHistory(false);
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
      if (interval) clearInterval(interval);
    };
  }, [
    session?.session_id,
    session?.status,
    mergeMessages,
    pollingInterval,
    fetchMessagesWithFilter,
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

  return {
    messages,
    displayMessages,
    isLoadingHistory,
    isTyping,
    showTypingIndicator,
    sendMessage,
    runUsageByUserMessageId,
  };
}
