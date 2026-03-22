import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import {
  sendMessageAction,
  type TaskEnqueueActionResult,
} from "@/features/chat/actions/session-actions";
import {
  getMessageAttachmentsDeltaRawAction,
  getMessagesBaseDeltaRawAction,
  getMessagesRawAction,
  getRunsBySessionAction,
} from "@/features/chat/actions/query-actions";
import type {
  ChatMessage,
  ExecutionSession,
  InputFile,
  UsageResponse,
} from "@/features/chat/types";
import {
  parseMessages,
  type RawApiMessage,
} from "@/features/chat/services/message-parser";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";

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
  sendMessage: (
    content: string,

    attachments?: InputFile[],
    modelSelection?: ModelSelection | null,
  ) => Promise<TaskEnqueueActionResult | null>;
  beginOptimisticRegenerate: (assistantMessageId: number) => string;
  beginOptimisticEditMessage: (args: {
    userMessageId: number;
    content: string;
  }) => string;
  commitOptimisticHistoryMutation: (mutationToken: string) => void;
  rollbackOptimisticHistoryMutation: (mutationToken: string) => void;
  reloadMessagesSnapshot: () => Promise<void>;
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

const DELTA_PAGE_SIZE = 500;
const MAX_DELTA_PAGES_PER_CYCLE = 5;

function mergeRawMessagesById(
  current: RawApiMessage[],
  appended: RawApiMessage[],
): RawApiMessage[] {
  if (appended.length === 0) return current;

  const byId = new Map<number, RawApiMessage>();
  current.forEach((message) => {
    byId.set(message.id, message);
  });

  appended.forEach((message) => {
    const existing = byId.get(message.id);
    if (!existing) {
      byId.set(message.id, message);
      return;
    }
    byId.set(message.id, {
      ...existing,
      ...message,
      attachments: message.attachments ?? existing.attachments,
    });
  });

  return Array.from(byId.values()).sort((a, b) => a.id - b.id);
}

function buildAttachmentSignature(attachments?: InputFile[] | null): string {
  if (!attachments || attachments.length === 0) {
    return "";
  }
  return attachments
    .map(
      (attachment) =>
        `${attachment.id ?? ""}|${attachment.source ?? ""}|${attachment.name ?? ""}|${attachment.url ?? ""}`,
    )
    .join("||");
}

function mergeServerAndOptimisticMessages(
  currentMessages: ChatMessage[],
  serverMessages: ChatMessage[],
): ChatMessage[] {
  const dedupedServerMessages = new Map<string, ChatMessage>();
  serverMessages.forEach((message) => {
    dedupedServerMessages.set(message.id, message);
  });
  const normalizedServerMessages = Array.from(
    dedupedServerMessages.values(),
  ).sort(compareMessagesForRenderOrder);

  const currentById = new Map(currentMessages.map((msg) => [msg.id, msg]));
  const finalMessages = normalizedServerMessages.map((serverMsg) => {
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

  currentMessages.forEach((localMsg) => {
    if (!localMsg.id.startsWith("msg-")) return;

    const isSynced = normalizedServerMessages.some((serverMsg) => {
      if (
        serverMsg.role !== localMsg.role ||
        serverMsg.content !== localMsg.content
      ) {
        return false;
      }

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

  return finalMessages.sort(compareMessagesForRenderOrder);
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
  const rawMessagesRef = useRef<RawApiMessage[]>([]);
  const [activeHistoryMutation, setActiveHistoryMutation] =
    useState<HistoryMutation | null>(null);
  const mutationRollbackMessagesRef = useRef<ChatMessage[] | null>(null);
  const activeMutationTokenRef = useRef<string | null>(null);
  const mutationSequenceRef = useRef(0);
  const messageCursorRef = useRef(0);
  const attachmentCursorRef = useRef(0);
  const attachmentsByMessageIdRef = useRef<Record<number, InputFile[]>>({});
  const messageDeltaInFlightRef = useRef<{
    sessionId: string;
    promise: Promise<{ changed: boolean; hasMore: boolean }>;
  } | null>(null);
  const attachmentDeltaInFlightRef = useRef<{
    sessionId: string;
    promise: Promise<{ changed: boolean; hasMore: boolean }>;
  } | null>(null);

  const buildParsedMessages = useCallback(() => {
    const realUserMessageIds = realUserMessageIdsRef.current ?? undefined;
    return parseMessages(rawMessagesRef.current, realUserMessageIds).messages;
  }, []);

  const fetchMessagesDelta = useCallback(
    async (
      sessionId: string,
      options?: {
        maxPages?: number;
      },
    ) => {
      const inFlight = messageDeltaInFlightRef.current;
      if (inFlight && inFlight.sessionId === sessionId) {
        return inFlight.promise;
      }

      const request = (async () => {
        if (lastLoadedSessionIdRef.current !== sessionId) {
          return { changed: false, hasMore: false };
        }

        const knownIds = new Set(
          rawMessagesRef.current.map((message) => message.id),
        );
        const appended: RawApiMessage[] = [];
        let afterMessageId = messageCursorRef.current;
        let hasMore = true;
        let guard = 0;
        const maxPages = Math.max(
          1,
          options?.maxPages ?? MAX_DELTA_PAGES_PER_CYCLE,
        );

        while (hasMore && guard < maxPages) {
          const payload = await getMessagesBaseDeltaRawAction({
            sessionId,
            afterMessageId,
            limit: DELTA_PAGE_SIZE,
          });
          if (lastLoadedSessionIdRef.current !== sessionId) {
            return { changed: false, hasMore: false };
          }
          for (const item of payload.items) {
            if (knownIds.has(item.id)) continue;
            knownIds.add(item.id);
            const attachments = attachmentsByMessageIdRef.current[item.id];
            appended.push(
              attachments && attachments.length > 0
                ? { ...item, attachments }
                : item,
            );
          }
          hasMore = payload.has_more;
          afterMessageId =
            payload.next_after_message_id ??
            payload.items.at(-1)?.id ??
            afterMessageId;
          if (afterMessageId > messageCursorRef.current) {
            messageCursorRef.current = afterMessageId;
          }
          guard += 1;
        }

        if (appended.length > 0) {
          rawMessagesRef.current = mergeRawMessagesById(
            rawMessagesRef.current,
            appended,
          );
        }

        return { changed: appended.length > 0, hasMore };
      })();

      messageDeltaInFlightRef.current = { sessionId, promise: request };
      try {
        return await request;
      } finally {
        if (messageDeltaInFlightRef.current?.promise === request) {
          messageDeltaInFlightRef.current = null;
        }
      }
    },
    [],
  );

  const fetchMessageAttachmentsDelta = useCallback(
    async (
      sessionId: string,
      options?: {
        maxPages?: number;
      },
    ) => {
      const inFlight = attachmentDeltaInFlightRef.current;
      if (inFlight && inFlight.sessionId === sessionId) {
        return inFlight.promise;
      }

      const request = (async () => {
        if (lastLoadedSessionIdRef.current !== sessionId) {
          return { changed: false, hasMore: false };
        }

        let afterMessageId = attachmentCursorRef.current;
        let hasMore = true;
        let guard = 0;
        let updatedMessages: RawApiMessage[] | null = null;
        let changed = false;
        const messageIndexById = new Map(
          rawMessagesRef.current.map((message, index) => [message.id, index]),
        );
        const maxPages = Math.max(
          1,
          options?.maxPages ?? MAX_DELTA_PAGES_PER_CYCLE,
        );

        while (hasMore && guard < maxPages) {
          const payload = await getMessageAttachmentsDeltaRawAction({
            sessionId,
            afterMessageId,
            limit: DELTA_PAGE_SIZE,
          });
          if (lastLoadedSessionIdRef.current !== sessionId) {
            return { changed: false, hasMore: false };
          }
          for (const item of payload.items) {
            const nextAttachments = item.attachments ?? [];
            const nextSignature = buildAttachmentSignature(nextAttachments);
            const previousAttachments =
              attachmentsByMessageIdRef.current[item.message_id] ?? [];
            const previousSignature =
              buildAttachmentSignature(previousAttachments);
            if (previousSignature === nextSignature) continue;

            attachmentsByMessageIdRef.current[item.message_id] =
              nextAttachments;
            const messageIndex = messageIndexById.get(item.message_id);
            if (messageIndex === undefined) continue;

            if (!updatedMessages) {
              updatedMessages = [...rawMessagesRef.current];
            }
            const currentMessage = updatedMessages[messageIndex];
            const currentSignature = buildAttachmentSignature(
              currentMessage.attachments,
            );
            if (currentSignature === nextSignature) continue;

            updatedMessages[messageIndex] = {
              ...currentMessage,
              attachments:
                nextAttachments.length > 0 ? nextAttachments : undefined,
            };
            changed = true;
          }

          hasMore = payload.has_more;
          afterMessageId =
            payload.next_after_message_id ??
            payload.items.at(-1)?.message_id ??
            afterMessageId;
          if (afterMessageId > attachmentCursorRef.current) {
            attachmentCursorRef.current = afterMessageId;
          }
          guard += 1;
        }

        if (updatedMessages) {
          rawMessagesRef.current = updatedMessages;
        }

        return { changed, hasMore };
      })();

      attachmentDeltaInFlightRef.current = { sessionId, promise: request };
      try {
        return await request;
      } finally {
        if (attachmentDeltaInFlightRef.current?.promise === request) {
          attachmentDeltaInFlightRef.current = null;
        }
      }
    },
    [],
  );

  const applyActiveHistoryMutation = useCallback(
    (input: ChatMessage[]) =>
      applyHistoryMutation(input, activeHistoryMutation),
    [activeHistoryMutation],
  );

  const syncMessagesFromServerState = useCallback(() => {
    const parsed = buildParsedMessages();
    setMessages((prev) =>
      applyActiveHistoryMutation(
        mergeServerAndOptimisticMessages(prev, parsed),
      ),
    );
  }, [applyActiveHistoryMutation, buildParsedMessages]);

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

      if (rawMessagesRef.current.length > 0) {
        syncMessagesFromServerState();
      }
    } catch (error) {
      console.error("[Chat] Failed to load runs:", error);
      realUserMessageIdsRef.current = null;
      setRunUsageByUserMessageId({});
    }
  }, [session?.session_id, syncMessagesFromServerState]);

  // Send message and immediately fetch updated messages
  const sendMessage = useCallback(
    async (
      content: string,
      attachments?: InputFile[],
      modelSelection?: ModelSelection | null,
    ): Promise<TaskEnqueueActionResult | null> => {
      if (!session?.session_id) return null;

      const normalizedContent = content.trim();
      const hasAttachments = (attachments?.length ?? 0) > 0;
      if (!normalizedContent && !hasAttachments) return null;

      const sessionId = session.session_id;
      const shouldOptimisticallyRender =
        session.status !== "running" && session.status !== "pending";
      let optimisticMessageId: string | null = null;

      if (shouldOptimisticallyRender) {
        const newMessage: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: "user",
          content: normalizedContent,
          status: "sent",
          timestamp: new Date().toISOString(),
          attachments,
        };

        optimisticMessageId = newMessage.id;
        setIsTyping(true);
        setMessages((prev) => [...prev, newMessage]);
      }

      try {
        const result = await sendMessageAction({
          sessionId,
          content: normalizedContent,
          attachments,
          model: modelSelection?.modelId,
          model_provider_id: modelSelection?.providerId,
        });

        // Refresh runs so multi-turn conversations only show real user inputs.
        await refreshRealUserMessageIds();

        const messageDelta = await fetchMessagesDelta(sessionId, {
          maxPages: 2,
        });
        if (messageDelta.changed) {
          syncMessagesFromServerState();
          void fetchMessageAttachmentsDelta(sessionId, { maxPages: 2 }).then(
            (attachmentDelta) => {
              if (attachmentDelta.changed) {
                syncMessagesFromServerState();
              }
            },
          );
        }

        return result;
      } catch (error) {
        console.error("[Chat] Failed to send message or get reply:", error);
        if (optimisticMessageId) {
          setMessages((prev) =>
            prev.filter((message) => message.id !== optimisticMessageId),
          );
          setIsTyping(false);
        }
        return null;
      }
    },
    [
      session,
      refreshRealUserMessageIds,
      fetchMessagesDelta,
      fetchMessageAttachmentsDelta,
      syncMessagesFromServerState,
    ],
  );

  const reloadMessagesSnapshot = useCallback(async (): Promise<void> => {
    const sessionId = session?.session_id;
    if (!sessionId) return;

    try {
      await refreshRealUserMessageIds();

      const rawMessages = await getMessagesRawAction({ sessionId });
      if (lastLoadedSessionIdRef.current !== sessionId) {
        return;
      }

      rawMessagesRef.current = rawMessages;
      messageCursorRef.current = rawMessages.at(-1)?.id ?? 0;
      attachmentCursorRef.current = rawMessages.at(-1)?.id ?? 0;
      attachmentsByMessageIdRef.current = rawMessages.reduce<
        Record<number, InputFile[]>
      >((acc, message) => {
        if ((message.attachments?.length ?? 0) > 0) {
          acc[message.id] = message.attachments ?? [];
        }
        return acc;
      }, {});

      syncMessagesFromServerState();
    } catch (error) {
      console.error("[Chat] Failed to reload message snapshot:", error);
    }
  }, [
    refreshRealUserMessageIds,
    session?.session_id,
    syncMessagesFromServerState,
  ]);

  // Load and poll for messages
  useEffect(() => {
    if (!session?.session_id) return;

    // Only set loading if it's a NEW session
    if (lastLoadedSessionIdRef.current !== session.session_id) {
      setIsLoadingHistory(true);
      setMessages([]);
      setIsTyping(false);
      realUserMessageIdsRef.current = null;
      rawMessagesRef.current = [];
      messageCursorRef.current = 0;
      attachmentCursorRef.current = 0;
      attachmentsByMessageIdRef.current = {};
      messageDeltaInFlightRef.current = null;
      attachmentDeltaInFlightRef.current = null;
      setActiveHistoryMutation(null);
      mutationRollbackMessagesRef.current = null;
      activeMutationTokenRef.current = null;
      setRunUsageByUserMessageId({});
      lastLoadedSessionIdRef.current = session.session_id;
    }

    let isCancelled = false;

    const fetchAttachments = async () => {
      try {
        const delta = await fetchMessageAttachmentsDelta(session.session_id);
        if (isCancelled) return;
        if (delta.changed) {
          syncMessagesFromServerState();
        }
        if (delta.hasMore && !isCancelled) {
          setTimeout(() => {
            if (!isCancelled) {
              void fetchAttachments();
            }
          }, 0);
        }
      } catch (error) {
        console.error("[Chat] Failed to load message attachments:", error);
      }
    };

    const fetchMessages = async (initial = false) => {
      try {
        const history = await fetchMessagesDelta(session.session_id);
        if (isCancelled) return;
        if (history.changed || initial) {
          syncMessagesFromServerState();
        }
        if (history.changed) {
          void fetchAttachments();
        }
        if (history.hasMore && !isCancelled) {
          setTimeout(() => {
            if (!isCancelled) {
              void fetchMessages(false);
            }
          }, 0);
        }
      } catch (error) {
        console.error("[Chat] Failed to load messages:", error);
      } finally {
        if (initial && !isCancelled) {
          setIsLoadingHistory(false);
        }
      }
    };

    void refreshRealUserMessageIds();
    void fetchMessages(true);

    // Setup polling
    let interval: NodeJS.Timeout;

    const isTerminal = ["completed", "failed", "canceled"].includes(
      session.status,
    );

    if (session.session_id && !isTerminal) {
      interval = setInterval(() => {
        void fetchMessages(false);
      }, pollingInterval);
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
    pollingInterval,
    fetchMessagesDelta,
    fetchMessageAttachmentsDelta,
    refreshRealUserMessageIds,
    syncMessagesFromServerState,
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
    reloadMessagesSnapshot,
    runUsageByUserMessageId,
  };
}
