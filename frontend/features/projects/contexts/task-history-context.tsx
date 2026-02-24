"use client";

import { createContext, useContext } from "react";
import type { TaskHistoryItem } from "@/features/projects/types";

interface TaskHistoryContextValue {
  refreshTasks: () => Promise<void>;
  touchTask: (
    taskId: string,
    updates: Partial<Omit<TaskHistoryItem, "id">> & { bumpToTop?: boolean },
  ) => void;
}

const TaskHistoryContext = createContext<TaskHistoryContextValue | null>(null);

export const TaskHistoryProvider = TaskHistoryContext.Provider;

export function useTaskHistoryContext() {
  const context = useContext(TaskHistoryContext);
  if (!context) {
    throw new Error(
      "useTaskHistoryContext must be used within TaskHistoryProvider",
    );
  }
  return context;
}
