"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { scheduledTasksService } from "@/features/scheduled-tasks/api/scheduled-tasks-api";
import type {
  ScheduledTask,
  ScheduledTaskCreateInput,
  ScheduledTaskUpdateInput,
} from "@/features/scheduled-tasks/types";
import type { RunResponse } from "@/features/chat/types/api/run";

export function useScheduledTasksStore() {
  const { t } = useT("translation");
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const latest = await scheduledTasksService.list();
      setTasks(latest);
    } catch (error) {
      console.error("[ScheduledTasks] refresh failed", error);
      toast.error(t("library.scheduledTasks.toasts.error"));
    }
  }, [t]);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const data = await scheduledTasksService.list();
        setTasks(data);
      } catch (error) {
        console.error("[ScheduledTasks] list failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [t]);

  const createTask = useCallback(
    async (input: ScheduledTaskCreateInput): Promise<ScheduledTask | null> => {
      setSavingId("create");
      try {
        const created = await scheduledTasksService.create(input);
        setTasks((prev) => [created, ...prev]);
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
    [t],
  );

  const updateTask = useCallback(
    async (taskId: string, input: ScheduledTaskUpdateInput) => {
      setSavingId(taskId);
      try {
        const updated = await scheduledTasksService.update(taskId, input);
        setTasks((prev) =>
          prev.map((item) =>
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
    [t],
  );

  const removeTask = useCallback(
    async (taskId: string) => {
      setSavingId(taskId);
      try {
        await scheduledTasksService.remove(taskId);
        setTasks((prev) =>
          prev.filter((item) => item.scheduled_task_id !== taskId),
        );
        toast.success(t("library.scheduledTasks.toasts.deleted"));
      } catch (error) {
        console.error("[ScheduledTasks] delete failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
      } finally {
        setSavingId(null);
      }
    },
    [t],
  );

  const triggerTask = useCallback(
    async (taskId: string) => {
      setSavingId(taskId);
      try {
        const resp = await scheduledTasksService.trigger(taskId);
        toast.success(t("library.scheduledTasks.toasts.triggered"));
        await refresh();
        return resp;
      } catch (error) {
        console.error("[ScheduledTasks] trigger failed", error);
        toast.error(t("library.scheduledTasks.toasts.error"));
        return null;
      } finally {
        setSavingId(null);
      }
    },
    [t, refresh],
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

  return {
    tasks,
    isLoading,
    savingId,
    refresh,
    createTask,
    updateTask,
    removeTask,
    triggerTask,
    listRuns,
  };
}
