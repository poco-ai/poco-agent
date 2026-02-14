"use client";

import { useCallback, useState } from "react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useT } from "@/lib/i18n/client";
import { scheduledTasksService } from "@/features/scheduled-tasks/services/scheduled-tasks-service";
import type {
  ScheduledTask,
  ScheduledTaskCreateInput,
  ScheduledTaskUpdateInput,
} from "@/features/scheduled-tasks/types";
import type { RunResponse } from "@/features/chat/types/api/run";

const SCHEDULED_TASKS_QUERY_KEY = ["scheduledTasks"] as const;

export function useScheduledTasksStore() {
  const { t } = useT("translation");
  const [savingId, setSavingId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({
    queryKey: SCHEDULED_TASKS_QUERY_KEY,
    queryFn: () => scheduledTasksService.list(),
  });

  const tasks = tasksQuery.data ?? [];

  const createTask = useCallback(
    async (input: ScheduledTaskCreateInput): Promise<ScheduledTask | null> => {
      setSavingId("create");
      try {
        const created = await scheduledTasksService.create(input);
        queryClient.setQueryData<ScheduledTask[]>(
          SCHEDULED_TASKS_QUERY_KEY,
          (prev) => [created, ...(prev ?? [])],
        );
        toast.success(t("library.scheduledTasks.toasts.created"));
        return created;
      } catch (error) {
        console.error("[ScheduledTasks] create failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
        return null;
      } finally {
        setSavingId(null);
      }
    },
    [queryClient, t],
  );

  const updateTask = useCallback(
    async (taskId: string, input: ScheduledTaskUpdateInput) => {
      setSavingId(taskId);
      try {
        const updated = await scheduledTasksService.update(taskId, input);
        queryClient.setQueryData<ScheduledTask[]>(
          SCHEDULED_TASKS_QUERY_KEY,
          (prev) =>
            (prev ?? []).map((item) =>
              item.scheduled_task_id === taskId ? updated : item,
            ),
        );
        toast.success(t("library.scheduledTasks.toasts.updated"));
      } catch (error) {
        console.error("[ScheduledTasks] update failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setSavingId(null);
      }
    },
    [queryClient, t],
  );

  const removeTask = useCallback(
    async (taskId: string) => {
      setSavingId(taskId);
      try {
        await scheduledTasksService.remove(taskId);
        queryClient.setQueryData<ScheduledTask[]>(
          SCHEDULED_TASKS_QUERY_KEY,
          (prev) =>
            (prev ?? []).filter((item) => item.scheduled_task_id !== taskId),
        );
        toast.success(t("library.scheduledTasks.toasts.deleted"));
      } catch (error) {
        console.error("[ScheduledTasks] delete failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setSavingId(null);
      }
    },
    [queryClient, t],
  );

  const triggerTask = useCallback(
    async (taskId: string) => {
      setSavingId(taskId);
      try {
        const resp = await scheduledTasksService.trigger(taskId);
        toast.success(t("library.scheduledTasks.toasts.triggered"));
        await queryClient.invalidateQueries({
          queryKey: SCHEDULED_TASKS_QUERY_KEY,
        });
        return resp;
      } catch (error) {
        console.error("[ScheduledTasks] trigger failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
        return null;
      } finally {
        setSavingId(null);
      }
    },
    [queryClient, t],
  );

  const listRuns = useCallback(
    async (taskId: string): Promise<RunResponse[]> => {
      try {
        return await scheduledTasksService.listRuns(taskId);
      } catch (error) {
        console.error("[ScheduledTasks] list runs failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
        return [];
      }
    },
    [t],
  );

  const refresh = useCallback(async () => {
    try {
      await tasksQuery.refetch();
    } catch (error) {
      console.error("[ScheduledTasks] refresh failed", error);
      toast.error(t("library.scheduledTasks.toasts.error"));
    }
  }, [t, tasksQuery]);

  return {
    tasks,
    isLoading: tasksQuery.isLoading,
    savingId,
    refresh,
    createTask,
    updateTask,
    removeTask,
    triggerTask,
    listRuns,
  };
}
