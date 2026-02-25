import { useCallback, useEffect, useRef, useState } from "react";
import { userInputService } from "@/features/chat/api/user-input-api";
import type { UserInputRequest } from "@/features/chat/types";

interface UseUserInputRequestsReturn {
  requests: UserInputRequest[];
  isLoading: boolean;
  error: Error | null;
  submitAnswer: (
    requestId: string,
    answers: Record<string, string>,
  ) => Promise<void>;
}

const POLLING_INTERVAL = 1500;

export function useUserInputRequests(
  sessionId?: string,
  enabled: boolean = true,
): UseUserInputRequestsReturn {
  const [requests, setRequests] = useState<UserInputRequest[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<number | null>(null);

  const fetchRequests = useCallback(async () => {
    if (!sessionId) {
      setRequests([]);
      return;
    }
    try {
      const result = await userInputService.listPending(sessionId);
      const now = Date.now();
      const filtered = result.filter((request) => {
        if (!request.expires_at) return true;
        const ts = new Date(request.expires_at).getTime();
        if (Number.isNaN(ts)) return true;
        return ts > now;
      });
      setRequests(filtered);
      setError(null);
    } catch (err) {
      setError(err as Error);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setRequests([]);
      return;
    }

    if (!enabled) {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setRequests([]);
      return;
    }

    fetchRequests();
    timerRef.current = window.setInterval(fetchRequests, POLLING_INTERVAL);

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [fetchRequests, sessionId, enabled]);

  const submitAnswer = useCallback(
    async (requestId: string, answers: Record<string, string>) => {
      setIsLoading(true);
      try {
        await userInputService.answer(requestId, { answers });
        setRequests((prev) => prev.filter((req) => req.id !== requestId));
        setError(null);
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return {
    requests,
    isLoading,
    error,
    submitAnswer,
  };
}
