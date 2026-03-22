"use client";

import * as React from "react";

import { capabilityRecommendationsService } from "@/features/task-composer/api/capability-recommendations-api";
import type { CapabilityRecommendation } from "@/features/task-composer/types/capability-recommendation";

const DEFAULT_DEBOUNCE_MS = 400;
const MIN_QUERY_LENGTH = 3;

export function useCapabilityRecommendations(
  query: string,
  options?: {
    debounceMs?: number;
    limit?: number;
    enabled?: boolean;
  },
) {
  const enabled = options?.enabled ?? true;
  const debounceMs = options?.debounceMs ?? DEFAULT_DEBOUNCE_MS;
  const limit = options?.limit ?? 3;

  const [items, setItems] = React.useState<CapabilityRecommendation[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [hasFetched, setHasFetched] = React.useState(false);

  const abortRef = React.useRef<AbortController | null>(null);

  const clearState = React.useCallback(() => {
    setItems([]);
    setIsLoading(false);
    setHasFetched(false);
  }, []);

  const fetchRecommendations = React.useCallback(
    async (cleanQuery: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);

      try {
        const response = await capabilityRecommendationsService.list(
          {
            query: cleanQuery,
            limit,
          },
          { signal: controller.signal },
        );

        if (controller.signal.aborted) return;
        setItems(response.items ?? []);
        setHasFetched(true);
      } catch (error) {
        if (controller.signal.aborted) return;
        console.warn("[CapabilityRecommendations] Failed to load:", error);
        setItems([]);
        setHasFetched(true);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [limit],
  );

  React.useEffect(() => {
    if (!enabled) {
      abortRef.current?.abort();
      clearState();
      return;
    }

    const cleanQuery = query.trim();
    if (cleanQuery.length < MIN_QUERY_LENGTH) {
      abortRef.current?.abort();
      clearState();
      return;
    }

    const timer = window.setTimeout(() => {
      void fetchRecommendations(cleanQuery);
    }, debounceMs);

    return () => window.clearTimeout(timer);
  }, [clearState, debounceMs, enabled, fetchRecommendations, query]);

  React.useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return {
    items,
    isLoading,
    hasFetched,
    minQueryLength: MIN_QUERY_LENGTH,
  };
}
