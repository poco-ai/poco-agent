import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  listTaskHistoryAction,
  moveTaskToProjectAction,
} from "@/features/projects/actions/project-actions";
import {
  deleteSessionAction,
  renameSessionTitleAction,
} from "@/features/chat/actions/session-actions";
import type { TaskHistoryItem } from "@/features/projects/types";
import { useT } from "@/lib/i18n/client";
import { toast } from "sonner";

interface UseTaskHistoryOptions {
  initialTasks?: TaskHistoryItem[];
}

const TASK_HISTORY_QUERY_KEY = ["taskHistory"] as const;

export function useTaskHistory(options: UseTaskHistoryOptions = {}) {
  const { initialTasks = [] } = options;
  const { t } = useT("translation");
  const queryClient = useQueryClient();

  const taskHistoryQuery = useQuery({
    queryKey: TASK_HISTORY_QUERY_KEY,
    queryFn: () => listTaskHistoryAction(),
    initialData: initialTasks,
  });

  const taskHistory = taskHistoryQuery.data ?? [];

  const addTask = useCallback(
    (
      title: string,
      options?: {
        timestamp?: string;
        status?: TaskHistoryItem["status"];
        projectId?: string;
        id?: string;
      },
    ) => {
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
      queryClient.setQueryData<TaskHistoryItem[]>(
        TASK_HISTORY_QUERY_KEY,
        (prev) => [newTask, ...(prev ?? [])],
      );
      return newTask;
    },
    [queryClient],
  );

  const touchTask = useCallback(
    (
      taskId: string,
      updates: Partial<Omit<TaskHistoryItem, "id">> & { bumpToTop?: boolean },
    ) => {
      queryClient.setQueryData<TaskHistoryItem[]>(
        TASK_HISTORY_QUERY_KEY,
        (prev) => {
          const list = prev ?? [];
          const idx = list.findIndex((task) => task.id === taskId);
          const { bumpToTop = true, ...taskUpdates } = updates;

          if (idx === -1) {
            const newTask: TaskHistoryItem = {
              id: taskId,
              title: taskUpdates.title ?? "",
              timestamp: taskUpdates.timestamp ?? new Date().toISOString(),
              status: taskUpdates.status ?? "pending",
              projectId: taskUpdates.projectId,
            };
            return [newTask, ...list];
          }

          const existing = list[idx];
          const updated: TaskHistoryItem = {
            ...existing,
            ...taskUpdates,
          };

          if (!bumpToTop) {
            const next = [...list];
            next[idx] = updated;
            return next;
          }

          const next = [...list];
          next.splice(idx, 1);
          return [updated, ...next];
        },
      );
    },
    [queryClient],
  );

  const removeMutation = useMutation({
    mutationFn: (taskId: string) => deleteSessionAction({ sessionId: taskId }),
    onMutate: async (taskId) => {
      await queryClient.cancelQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
      const previousTasks =
        queryClient.getQueryData<TaskHistoryItem[]>(TASK_HISTORY_QUERY_KEY) ??
        [];
      queryClient.setQueryData<TaskHistoryItem[]>(
        TASK_HISTORY_QUERY_KEY,
        (prev) => (prev ?? []).filter((task) => task.id !== taskId),
      );
      return { previousTasks };
    },
    onError: (error, _taskId, ctx) => {
      console.error("Failed to delete task", error);
      if (ctx?.previousTasks) {
        queryClient.setQueryData<TaskHistoryItem[]>(
          TASK_HISTORY_QUERY_KEY,
          ctx.previousTasks,
        );
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
    },
  });

  const removeTask = useCallback(
    async (taskId: string) => {
      try {
        await removeMutation.mutateAsync(taskId);
      } catch {
        // Handled by mutation error/rollback.
      }
    },
    [removeMutation],
  );

  const moveMutation = useMutation({
    mutationFn: (input: { taskId: string; projectId: string | null }) =>
      moveTaskToProjectAction({
        sessionId: input.taskId,
        projectId: input.projectId,
      }),
    onMutate: async ({ taskId, projectId }) => {
      await queryClient.cancelQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
      const previousTasks =
        queryClient.getQueryData<TaskHistoryItem[]>(TASK_HISTORY_QUERY_KEY) ??
        [];

      queryClient.setQueryData<TaskHistoryItem[]>(
        TASK_HISTORY_QUERY_KEY,
        (prev) =>
          (prev ?? []).map((task) =>
            task.id === taskId
              ? { ...task, projectId: projectId ?? undefined }
              : task,
          ),
      );

      return { previousTasks };
    },
    onError: (error, _input, ctx) => {
      console.error("Failed to move task to project", error);
      if (ctx?.previousTasks) {
        queryClient.setQueryData<TaskHistoryItem[]>(
          TASK_HISTORY_QUERY_KEY,
          ctx.previousTasks,
        );
      }
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
    },
  });

  const moveTask = useCallback(
    async (taskId: string, projectId: string | null) => {
      try {
        await moveMutation.mutateAsync({ taskId, projectId });
      } catch {
        // Handled by mutation error/rollback.
      }
    },
    [moveMutation],
  );

  const renameMutation = useMutation({
    mutationFn: (input: { taskId: string; title: string }) =>
      renameSessionTitleAction({ sessionId: input.taskId, title: input.title }),
    onMutate: async ({ taskId, title }) => {
      await queryClient.cancelQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
      const previousTasks =
        queryClient.getQueryData<TaskHistoryItem[]>(TASK_HISTORY_QUERY_KEY) ??
        [];

      queryClient.setQueryData<TaskHistoryItem[]>(
        TASK_HISTORY_QUERY_KEY,
        (prev) =>
          (prev ?? []).map((task) =>
            task.id === taskId ? { ...task, title } : task,
          ),
      );

      return { previousTasks };
    },
    onSuccess: () => {
      toast.success(t("task.toasts.renamed"));
    },
    onError: (error, _input, ctx) => {
      console.error("Failed to rename task", error);
      if (ctx?.previousTasks) {
        queryClient.setQueryData<TaskHistoryItem[]>(
          TASK_HISTORY_QUERY_KEY,
          ctx.previousTasks,
        );
      }
      toast.error(t("task.toasts.renameFailed"));
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: TASK_HISTORY_QUERY_KEY });
    },
  });

  const renameTask = useCallback(
    async (taskId: string, newTitle: string) => {
      try {
        await renameMutation.mutateAsync({ taskId, title: newTitle });
      } catch {
        // Handled by mutation error/rollback.
      }
    },
    [renameMutation],
  );

  return {
    taskHistory,
    isLoading: taskHistoryQuery.isLoading,
    addTask,
    touchTask,
    removeTask,
    moveTask,
    renameTask,
    refreshTasks: async () => {
      await taskHistoryQuery.refetch();
    },
  };
}
