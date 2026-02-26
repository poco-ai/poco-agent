"use client";

import { useCallback } from "react";
import type { TaskHistoryItem } from "@/features/projects/types";

interface UseProjectDeletionOptions {
  taskHistory: TaskHistoryItem[];
  moveTask: (taskId: string, projectId: string | null) => Promise<void> | void;
  removeProject: (projectId: string) => Promise<void>;
}

export function useProjectDeletion({
  taskHistory,
  moveTask,
  removeProject,
}: UseProjectDeletionOptions) {
  return useCallback(
    async (projectId: string) => {
      const affectedTasks = taskHistory.filter(
        (task) => task.projectId === projectId,
      );

      await Promise.all(
        affectedTasks.map((task) => Promise.resolve(moveTask(task.id, null))),
      );

      await removeProject(projectId);
    },
    [taskHistory, moveTask, removeProject],
  );
}
