import { useState, useCallback, useMemo } from "react";
import type { TaskHistoryItem } from "@/features/projects";

interface UseProjectExpansionOptions {
  taskHistory: TaskHistoryItem[];
  activeTaskId?: string;
}

interface UseProjectExpansionResult {
  expandedProjects: Set<string>;
  toggleProjectExpanded: (projectId: string) => void;
}

/**
 * Hook to manage project expand/collapse state in the sidebar.
 * Auto-expands project when navigating to a session within it.
 */
export function useProjectExpansion({
  taskHistory,
  activeTaskId,
}: UseProjectExpansionOptions): UseProjectExpansionResult {
  const [manuallyExpanded, setManuallyExpanded] = useState<Set<string>>(
    new Set(),
  );

  // Derive the project that should be auto-expanded based on active task
  const autoExpandedProjectId = useMemo(() => {
    if (!activeTaskId || typeof activeTaskId !== "string") return undefined;
    const activeTask = taskHistory.find((task) => task.id === activeTaskId);
    return activeTask?.projectId;
  }, [activeTaskId, taskHistory]);

  // Combine manually expanded projects with auto-expanded project
  const expandedProjects = useMemo(() => {
    const result = new Set(manuallyExpanded);
    if (autoExpandedProjectId) {
      result.add(autoExpandedProjectId);
    }
    return result;
  }, [manuallyExpanded, autoExpandedProjectId]);

  const toggleProjectExpanded = useCallback((projectId: string) => {
    setManuallyExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  }, []);

  return {
    expandedProjects,
    toggleProjectExpanded,
  };
}
