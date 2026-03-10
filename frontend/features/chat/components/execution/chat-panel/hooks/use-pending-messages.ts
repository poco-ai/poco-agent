import { useEffect, useState, useRef, useCallback } from "react";
import type { ExecutionSession, InputFile } from "@/features/chat/types";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";

interface UsePendingMessagesOptions {
  session: ExecutionSession | null;
  sendMessage: (
    content: string,
    attachments?: InputFile[],
    modelSelection?: ModelSelection | null,
  ) => Promise<void>;
}

export interface PendingMessage {
  content: string;
  attachments?: InputFile[];
  modelSelection?: ModelSelection | null;
}

interface UsePendingMessagesReturn {
  pendingMessages: PendingMessage[];
  isSendingPending: boolean;
  addPendingMessage: (
    content: string,
    attachments?: InputFile[],
    modelSelection?: ModelSelection | null,
  ) => void;
  sendPendingMessage: (index: number) => Promise<void>;
  modifyPendingMessage: (index: number) => PendingMessage;
  deletePendingMessage: (index: number) => void;
}

/**
 * Manages pending message queue and auto-send logic
 *
 * Responsibilities:
 * - Queue messages when session is active
 * - Auto-send pending messages when session becomes idle
 * - Handle manual send/modify/delete from queue
 * - Prevent concurrent auto-sends
 */
export function usePendingMessages({
  session,
  sendMessage,
}: UsePendingMessagesOptions): UsePendingMessagesReturn {
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([]);
  const [isSendingPending, setIsSendingPending] = useState(false);
  const isProcessingRef = useRef(false);

  // Determine if session is running/active
  const isSessionActive =
    session?.status === "running" || session?.status === "pending";
  const isSessionCanceled = session?.status === "canceled";

  // Reset auto-send lock when session becomes active
  useEffect(() => {
    if (isSessionActive) {
      isProcessingRef.current = false;
      setIsSendingPending(false);
    }
  }, [isSessionActive]);

  // Add message to pending queue
  const addPendingMessage = useCallback(
    (
      content: string,
      attachments?: InputFile[],
      modelSelection?: ModelSelection | null,
    ) => {
      setPendingMessages((prev) => [
        ...prev,
        { content, attachments, modelSelection },
      ]);
    },
    [],
  );

  // Send a specific pending message by index
  const sendPendingMessage = useCallback(
    async (index: number) => {
      const msg = pendingMessages[index];
      setPendingMessages((prev) => prev.filter((_, i) => i !== index));
      await sendMessage(msg.content, msg.attachments, msg.modelSelection);
    },
    [pendingMessages, sendMessage],
  );

  // Modify a pending message (returns content/attachments for editing)
  const modifyPendingMessage = useCallback(
    (index: number) => {
      const msg = pendingMessages[index];
      setPendingMessages((prev) => prev.filter((_, i) => i !== index));
      return msg;
    },
    [pendingMessages],
  );

  // Delete a pending message
  const deletePendingMessage = useCallback((index: number) => {
    setPendingMessages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Auto-send pending messages when session is idle
  useEffect(() => {
    const autoSend = async () => {
      // Only send if session is NOT active AND we are NOT currently sending
      if (
        !isSessionActive &&
        !isSessionCanceled &&
        pendingMessages.length > 0 &&
        !isProcessingRef.current
      ) {
        isProcessingRef.current = true;
        setIsSendingPending(true);
        const msg = pendingMessages[0];
        setPendingMessages((prev) => prev.slice(1));

        try {
          await sendMessage(msg.content, msg.attachments, msg.modelSelection);
        } catch (error) {
          console.error("Auto-send failed:", error);
        } finally {
          isProcessingRef.current = false;
          setIsSendingPending(false);
        }
      }
    };
    autoSend();
  }, [isSessionActive, isSessionCanceled, pendingMessages, sendMessage]);

  return {
    pendingMessages,
    isSendingPending,
    addPendingMessage,
    sendPendingMessage,
    modifyPendingMessage,
    deletePendingMessage,
  };
}
