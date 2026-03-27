"use client";

import * as React from "react";

import { getDeliverableVersionToolExecutionsAction } from "@/features/chat/actions/query-actions";
import type { ToolExecutionResponse } from "@/features/chat/types";
import { useToolExecutions } from "./use-tool-executions";

interface UseDeliverableToolExecutionsOptions {
  sessionId?: string;
  versionId?: string | null;
  mode?: "deliverable" | "session";
  isActive?: boolean;
  pollingIntervalMs?: number;
  limit?: number;
}

export function useDeliverableToolExecutions({
  sessionId,
  versionId,
  mode = "session",
  isActive = false,
  pollingIntervalMs = 2000,
  limit = 500,
}: UseDeliverableToolExecutionsOptions) {
  const sessionExecutions = useToolExecutions({
    sessionId,
    isActive,
    pollingIntervalMs,
    limit,
  });
  const [deliverableExecutions, setDeliverableExecutions] = React.useState<
    ToolExecutionResponse[]
  >([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);

  const fetchDeliverableExecutions = React.useCallback(async () => {
    if (!sessionId || !versionId || mode !== "deliverable") {
      setDeliverableExecutions([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    try {
      const items = await getDeliverableVersionToolExecutionsAction({
        sessionId,
        versionId,
      });
      setDeliverableExecutions(items);
      setError(null);
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setIsLoading(false);
    }
  }, [mode, sessionId, versionId]);

  React.useEffect(() => {
    void fetchDeliverableExecutions();
  }, [fetchDeliverableExecutions]);

  React.useEffect(() => {
    if (!sessionId || !versionId || mode !== "deliverable" || !isActive) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      void fetchDeliverableExecutions();
    }, pollingIntervalMs);
    return () => window.clearInterval(timer);
  }, [
    fetchDeliverableExecutions,
    isActive,
    mode,
    pollingIntervalMs,
    sessionId,
    versionId,
  ]);

  if (mode !== "deliverable" || !versionId) {
    return sessionExecutions;
  }

  return {
    executions: deliverableExecutions,
    isLoading,
    isLoadingMore: false,
    hasMore: false,
    error,
    refetch: fetchDeliverableExecutions,
    loadMore: () => undefined,
  };
}
