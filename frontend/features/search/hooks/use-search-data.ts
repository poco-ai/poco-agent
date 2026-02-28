"use client";

import * as React from "react";
import type {
  SearchResultTask,
  SearchResultProject,
  SearchResultMessage,
} from "@/features/search/types";
import { searchService } from "@/features/search/api/search-api";

/**
 * Hook for fetching and aggregating search data
 */
export function useSearchData(
  query: string,
  options?: {
    enabled?: boolean;
    debounceMs?: number;
    projectId?: string | null;
    limitTasks?: number;
    limitProjects?: number;
    limitMessages?: number;
  },
) {
  const enabled = options?.enabled ?? true;
  const debounceMs = options?.debounceMs ?? 200;

  const [tasks, setTasks] = React.useState<SearchResultTask[]>([]);
  const [projects, setProjects] = React.useState<SearchResultProject[]>([]);
  const [messages, setMessages] = React.useState<SearchResultMessage[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);

  const abortRef = React.useRef<AbortController | null>(null);

  const clearResults = React.useCallback(() => {
    setTasks([]);
    setProjects([]);
    setMessages([]);
  }, []);

  const fetchData = React.useCallback(
    async (q: string) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      setError(null);

      try {
        const data = await searchService.globalSearch(
          {
            q,
            project_id: options?.projectId ?? undefined,
            limit_tasks: options?.limitTasks,
            limit_projects: options?.limitProjects,
            limit_messages: options?.limitMessages,
          },
          { signal: controller.signal },
        );

        if (controller.signal.aborted) return;
        setTasks(data.tasks);
        setProjects(data.projects);
        setMessages(data.messages);
      } catch (err) {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err : new Error("Search failed"));
        clearResults();
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [
      clearResults,
      options?.limitMessages,
      options?.limitProjects,
      options?.limitTasks,
      options?.projectId,
    ],
  );

  React.useEffect(() => {
    if (!enabled) return;

    const q = query.trim();
    if (!q) {
      abortRef.current?.abort();
      setIsLoading(false);
      setError(null);
      clearResults();
      return;
    }

    const handle = window.setTimeout(() => {
      void fetchData(q);
    }, debounceMs);

    return () => window.clearTimeout(handle);
  }, [debounceMs, enabled, fetchData, query, clearResults]);

  React.useEffect(() => {
    if (enabled) return;
    abortRef.current?.abort();
    setIsLoading(false);
    setError(null);
    clearResults();
  }, [clearResults, enabled]);

  React.useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const refetch = React.useCallback(() => {
    const q = query.trim();
    if (!q) return;
    void fetchData(q);
  }, [fetchData, query]);

  return {
    tasks,
    projects,
    messages,
    isLoading,
    error,
    refetch,
    disabled: !enabled,
  };
}
