"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import {
  listTaskHistoryAction,
  moveTaskToProjectAction,
} from "@/features/projects/actions/project-actions";
import { renameSessionTitleAction } from "@/features/chat/actions/session-actions";
import type {
  AddTaskOptions,
  TaskHistoryItem,
} from "@/features/projects/types";
import { useT } from "@/lib/i18n/client";
import {
  getStartupPreloadPromise,
  getStartupPreloadValue,
  hasStartupPreloadValue,
} from "@/lib/startup-preload";
import { toast } from "sonner";

interface UseTaskHistoryOptions {
  initialTasks?: TaskHistoryItem[];
}

export function useTaskHistory(options: UseTaskHistoryOptions = {}) {
  const preloadTasks = getStartupPreloadValue("taskHistory");
  const hasPreloadedTasks = hasStartupPreloadValue("taskHistory");
  const { initialTasks = [] } = options;
  const seededTasks = hasPreloadedTasks ? (preloadTasks ?? []) : initialTasks;
  const { t } = useT("translation");
  const hasConsumedStartupPreloadRef = useRef(hasPreloadedTasks);
  const [taskHistory, setTaskHistory] =
    useState<TaskHistoryItem[]>(seededTasks);
  const [isLoading, setIsLoading] = useState(
    !hasPreloadedTasks && !initialTasks.length,
  );

  const fetchTasks = useCallback(async () => {
    try {
      setIsLoading(true);
      // Startup preload is a static snapshot. Use it only once to avoid
      // clobbering runtime updates when refreshTasks() is called later.
      if (!hasConsumedStartupPreloadRef.current) {
        hasConsumedStartupPreloadRef.current = true;

        if (hasStartupPreloadValue("taskHistory")) {
          setTaskHistory(getStartupPreloadValue("taskHistory") ?? []);
          return;
        }

        const preloadPromise = getStartupPreloadPromise();
        if (preloadPromise) {
          await preloadPromise;
          if (hasStartupPreloadValue("taskHistory")) {
            setTaskHistory(getStartupPreloadValue("taskHistory") ?? []);
            return;
          }
        }
      }

      const data = await listTaskHistoryAction();
      setTaskHistory(data);
    } catch (error) {
      console.error("Failed to fetch task history", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const addTask = useCallback((title: string, options?: AddTaskOptions) => {
    const newTask: TaskHistoryItem = {
      // Use sessionId if provided, otherwise fallback to random (for optimistic updates)
      id:
        options?.id ||
        `task-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      title,
      timestamp: options?.timestamp || new Date().toISOString(),
      status: options?.status || "pending",
      projectId: options?.projectId,
    };
    setTaskHistory((prev) => [newTask, ...prev]);
    return newTask;
  }, []);

  const touchTask = useCallback(
    (
      taskId: string,
      updates: Partial<Omit<TaskHistoryItem, "id">> & { bumpToTop?: boolean },
    ) => {
      setTaskHistory((prev) => {
        const idx = prev.findIndex((task) => task.id === taskId);
        const { bumpToTop = true, ...taskUpdates } = updates;

        if (idx === -1) {
          const newTask: TaskHistoryItem = {
            id: taskId,
            title: taskUpdates.title ?? "",
            timestamp: taskUpdates.timestamp ?? new Date().toISOString(),
            status: taskUpdates.status ?? "pending",
            projectId: taskUpdates.projectId,
          };
          return [newTask, ...prev];
        }

        const existing = prev[idx];
        const updated: TaskHistoryItem = {
          ...existing,
          ...taskUpdates,
        };

        if (!bumpToTop) {
          const next = [...prev];
          next[idx] = updated;
          return next;
        }

        const next = [...prev];
        next.splice(idx, 1);
        return [updated, ...next];
      });
    },
    [],
  );

  const removeTask = useCallback(
    async (taskId: string) => {
      // Optimistic update
      const previousTasks = taskHistory;
      setTaskHistory((prev) => prev.filter((task) => task.id !== taskId));

      try {
        const { deleteSessionAction } =
          await import("@/features/chat/actions/session-actions");
        await deleteSessionAction({ sessionId: taskId });
      } catch (error) {
        console.error("Failed to delete task", error);
        // Rollback on error
        setTaskHistory(previousTasks);
      }
    },
    [taskHistory],
  );

  const moveTask = useCallback(
    async (taskId: string, projectId: string | null) => {
      let previousTasks: TaskHistoryItem[] = [];
      setTaskHistory((prev) => {
        previousTasks = prev;
        return prev.map((task) =>
          task.id === taskId
            ? { ...task, projectId: projectId ?? undefined }
            : task,
        );
      });

      try {
        await moveTaskToProjectAction({
          sessionId: taskId,
          projectId: projectId ?? null,
        });
      } catch (error) {
        console.error("Failed to move task to project", error);
        setTaskHistory(previousTasks);
      }
    },
    [],
  );

  const renameTask = useCallback(
    async (taskId: string, newTitle: string) => {
      let previousTasks: TaskHistoryItem[] = [];
      setTaskHistory((prev) => {
        previousTasks = prev;
        return prev.map((task) =>
          task.id === taskId ? { ...task, title: newTitle } : task,
        );
      });

      try {
        await renameSessionTitleAction({ sessionId: taskId, title: newTitle });
        toast.success(t("task.toasts.renamed"));
      } catch (error) {
        console.error("Failed to rename task", error);
        setTaskHistory(previousTasks);
        toast.error(t("task.toasts.renameFailed"));
      }
    },
    [t],
  );

  return {
    taskHistory,
    isLoading,
    addTask,
    touchTask,
    removeTask,
    moveTask,
    renameTask,
    refreshTasks: fetchTasks,
  };
}
