"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { pendingSkillCreationService } from "@/features/chat/api/pending-skill-creation-api";
import type {
  PendingSkillCreation,
  PendingSkillCreationCancelInput,
  PendingSkillCreationConfirmInput,
} from "@/features/chat/types";

const POLLING_INTERVAL = 2000;

interface UsePendingSkillCreationsReturn {
  creations: PendingSkillCreation[];
  activeCreation: PendingSkillCreation | null;
  isLoading: boolean;
  isSubmitting: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  confirmCreation: (
    creationId: string,
    payload: PendingSkillCreationConfirmInput,
  ) => Promise<PendingSkillCreation>;
  cancelCreation: (
    creationId: string,
    payload?: PendingSkillCreationCancelInput,
  ) => Promise<PendingSkillCreation>;
}

export function usePendingSkillCreations(
  sessionId?: string,
  enabled: boolean = true,
): UsePendingSkillCreationsReturn {
  const [creations, setCreations] = useState<PendingSkillCreation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<number | null>(null);

  const fetchCreations = useCallback(async () => {
    if (!sessionId) {
      setCreations([]);
      return;
    }

    try {
      setIsLoading(true);
      const result = await pendingSkillCreationService.listPending(sessionId);
      setCreations(result);
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || !enabled) {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setCreations([]);
      return;
    }

    void fetchCreations();
    timerRef.current = window.setInterval(() => {
      void fetchCreations();
    }, POLLING_INTERVAL);

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [enabled, fetchCreations, sessionId]);

  const confirmCreation = useCallback(
    async (
      creationId: string,
      payload: PendingSkillCreationConfirmInput,
    ): Promise<PendingSkillCreation> => {
      setIsSubmitting(true);
      try {
        const result = await pendingSkillCreationService.confirm(
          creationId,
          payload,
        );
        setCreations((prev) => prev.filter((item) => item.id !== creationId));
        setError(null);
        return result;
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  const cancelCreation = useCallback(
    async (
      creationId: string,
      payload?: PendingSkillCreationCancelInput,
    ): Promise<PendingSkillCreation> => {
      setIsSubmitting(true);
      try {
        const result = await pendingSkillCreationService.cancel(
          creationId,
          payload,
        );
        setCreations((prev) => prev.filter((item) => item.id !== creationId));
        setError(null);
        return result;
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [],
  );

  return {
    creations,
    activeCreation: creations[0] ?? null,
    isLoading,
    isSubmitting,
    error,
    refresh: fetchCreations,
    confirmCreation,
    cancelCreation,
  };
}
