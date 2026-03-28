import { useEffect, useState, useRef, useCallback } from "react";
import {
  deleteQueuedQueryAction,
  sendQueuedQueryNowAction,
  type TaskEnqueueActionResult,
} from "@/features/chat/actions/session-actions";
import { getQueuedQueriesAction } from "@/features/chat/actions/query-actions";
import { deriveExecutionSessionState } from "@/features/chat/lib/execution-session-state";
import type { ExecutionSession, InputFile } from "@/features/chat/types";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";

const PENDING_MESSAGE_POLLING_INTERVAL = 3000;

interface UsePendingMessagesOptions {
  session: ExecutionSession | null;
}

export interface PendingMessage {
  id: string;
  content: string;
  attachments?: InputFile[];
  modelSelection?: ModelSelection | null;
  status: "queued" | "paused";
  sequenceNo: number;
}

interface UsePendingMessagesReturn {
  pendingMessages: PendingMessage[];
  isLoadingPendingMessages: boolean;
  addPendingMessage: (
    message: Omit<PendingMessage, "sequenceNo"> & { sequenceNo?: number },
  ) => void;
  refreshPendingMessages: () => Promise<void>;
  sendPendingMessage: (
    messageId: string,
  ) => Promise<TaskEnqueueActionResult | null>;
  modifyPendingMessage: (messageId: string) => Promise<PendingMessage | null>;
  deletePendingMessage: (messageId: string) => Promise<void>;
}

function toPendingMessage(item: {
  queue_item_id: string;
  prompt: string;
  attachments?: InputFile[];
  status: "queued" | "paused" | "promoted" | "canceled";
  sequence_no: number;
}): PendingMessage {
  return {
    id: item.queue_item_id,
    content: item.prompt,
    attachments: item.attachments ?? undefined,
    status: item.status === "paused" ? "paused" : "queued",
    sequenceNo: item.sequence_no,
  };
}

function sortPendingMessages(messages: PendingMessage[]): PendingMessage[] {
  return [...messages].sort((left, right) => {
    if (left.sequenceNo !== right.sequenceNo) {
      return left.sequenceNo - right.sequenceNo;
    }
    return left.id.localeCompare(right.id);
  });
}

export function usePendingMessages({
  session,
}: UsePendingMessagesOptions): UsePendingMessagesReturn {
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([]);
  const [isLoadingPendingMessages, setIsLoadingPendingMessages] =
    useState(false);
  const lastLoadedSessionIdRef = useRef<string | null>(null);
  const requestIdRef = useRef(0);

  const sessionId = session?.session_id ?? null;
  const executionState = deriveExecutionSessionState(session);
  const shouldPoll =
    Boolean(sessionId) &&
    (executionState.isRunActive ||
      pendingMessages.length > 0 ||
      executionState.hasQueuedQueries);

  const refreshPendingMessages = useCallback(async () => {
    if (!sessionId) {
      lastLoadedSessionIdRef.current = null;
      setPendingMessages([]);
      setIsLoadingPendingMessages(false);
      return;
    }

    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setIsLoadingPendingMessages(true);

    try {
      const items = await getQueuedQueriesAction({ sessionId });
      if (requestIdRef.current !== requestId) return;
      lastLoadedSessionIdRef.current = sessionId;

      // Check for duplicate/undefined IDs
      const ids = items.map((item) => item?.queue_item_id);
      const uniqueIds = new Set(ids);
      if (ids.length !== uniqueIds.size) {
        console.error("[PendingMessages] Duplicate IDs detected!", {
          ids,
          items,
        });
      }
      const undefinedIds = items.filter((item) => !item?.queue_item_id);
      if (undefinedIds.length > 0) {
        console.error(
          "[PendingMessages] Items with undefined IDs:",
          undefinedIds,
        );
      }

      const messages = items.map(toPendingMessage);
      setPendingMessages(sortPendingMessages(messages));
    } catch (error) {
      console.error("[PendingMessages] Failed to load queued queries:", error);
      if (requestIdRef.current !== requestId) return;
    } finally {
      if (requestIdRef.current === requestId) {
        setIsLoadingPendingMessages(false);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      lastLoadedSessionIdRef.current = null;
      setPendingMessages([]);
      setIsLoadingPendingMessages(false);
      return;
    }

    if (lastLoadedSessionIdRef.current !== sessionId) {
      setPendingMessages([]);
    }

    void refreshPendingMessages();
  }, [refreshPendingMessages, sessionId]);

  useEffect(() => {
    if (!shouldPoll || !sessionId) return;

    const interval = window.setInterval(() => {
      void refreshPendingMessages();
    }, PENDING_MESSAGE_POLLING_INTERVAL);

    return () => {
      window.clearInterval(interval);
    };
  }, [refreshPendingMessages, sessionId, shouldPoll]);

  const addPendingMessage = useCallback(
    (message: Omit<PendingMessage, "sequenceNo"> & { sequenceNo?: number }) => {
      setPendingMessages((prev) => {
        const maxSequenceNo = prev.reduce(
          (max, item) => Math.max(max, item.sequenceNo),
          0,
        );
        const existingIndex = prev.findIndex((item) => item.id === message.id);
        const existingMessage =
          existingIndex >= 0 ? prev[existingIndex] : undefined;
        const nextMessage: PendingMessage = {
          ...message,
          sequenceNo:
            message.sequenceNo ??
            existingMessage?.sequenceNo ??
            maxSequenceNo + 1,
        };

        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = nextMessage;
          return sortPendingMessages(updated);
        }

        return sortPendingMessages([...prev, nextMessage]);
      });
    },
    [],
  );

  const deletePendingMessage = useCallback(
    async (messageId: string) => {
      if (!sessionId) return;

      const previousMessages = pendingMessages;
      setPendingMessages((prev) =>
        prev.filter((item) => item.id !== messageId),
      );

      try {
        await deleteQueuedQueryAction({ sessionId, itemId: messageId });
      } catch (error) {
        setPendingMessages(previousMessages);
        void refreshPendingMessages();
        throw error;
      }
    },
    [pendingMessages, refreshPendingMessages, sessionId],
  );

  const modifyPendingMessage = useCallback(
    async (messageId: string) => {
      const target = pendingMessages.find((item) => item.id === messageId);
      if (!target) return null;

      await deletePendingMessage(messageId);
      return target;
    },
    [deletePendingMessage, pendingMessages],
  );

  const sendPendingMessage = useCallback(
    async (messageId: string) => {
      if (!sessionId) return null;

      try {
        const result = await sendQueuedQueryNowAction({
          sessionId,
          itemId: messageId,
        });
        await refreshPendingMessages();
        return result;
      } catch (error) {
        console.error("[PendingMessages] Failed to send queued query:", error);
        void refreshPendingMessages();
        return null;
      }
    },
    [refreshPendingMessages, sessionId],
  );

  return {
    pendingMessages,
    isLoadingPendingMessages,
    addPendingMessage,
    refreshPendingMessages,
    sendPendingMessage,
    modifyPendingMessage,
    deletePendingMessage,
  };
}
