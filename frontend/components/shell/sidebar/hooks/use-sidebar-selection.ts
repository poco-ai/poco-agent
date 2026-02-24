"use client";

import * as React from "react";

/**
 * Manages the batch selection state for sidebar tasks and projects.
 *
 * Encapsulates:
 * - Selection mode toggle
 * - Task and project selection sets
 * - Keyboard shortcut (Escape to cancel)
 * - Batch delete orchestration
 */
export function useSidebarSelection(handlers: {
  onDeleteTask: (taskId: string) => Promise<void> | void;
  onDeleteProject?: (projectId: string) => Promise<void> | void;
}) {
  const [selectionKind, setSelectionKind] = React.useState<
    "tasks" | "projects" | null
  >(null);
  const [selectedTaskIds, setSelectedTaskIds] = React.useState<Set<string>>(
    new Set(),
  );
  const [selectedProjectIds, setSelectedProjectIds] = React.useState<
    Set<string>
  >(new Set());

  const enterTaskSelectionMode = React.useCallback(() => {
    setSelectionKind("tasks");
    setSelectedTaskIds(new Set());
    setSelectedProjectIds(new Set());
  }, []);

  const enterProjectSelectionMode = React.useCallback(() => {
    setSelectionKind("projects");
    setSelectedProjectIds(new Set());
    setSelectedTaskIds(new Set());
  }, []);

  // ---- Task selection ----

  const enableTaskSelectionMode = React.useCallback((taskId: string) => {
    setSelectionKind("tasks");
    setSelectedTaskIds(new Set([taskId]));
    setSelectedProjectIds(new Set());
  }, []);

  const toggleTaskSelection = React.useCallback((taskId: string) => {
    setSelectedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }, []);

  // ---- Project selection ----

  const enableProjectSelectionMode = React.useCallback((projectId: string) => {
    setSelectionKind("projects");
    setSelectedProjectIds(new Set([projectId]));
    setSelectedTaskIds(new Set());
  }, []);

  const toggleProjectSelection = React.useCallback((projectId: string) => {
    setSelectedProjectIds((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) next.delete(projectId);
      else next.add(projectId);
      return next;
    });
  }, []);

  // ---- Cancel ----

  const cancelSelectionMode = React.useCallback(() => {
    setSelectionKind(null);
    setSelectedTaskIds(new Set());
    setSelectedProjectIds(new Set());
  }, []);

  // Escape key handler
  React.useEffect(() => {
    if (!selectionKind) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") cancelSelectionMode();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectionKind, cancelSelectionMode]);

  // ---- Batch delete ----

  const deleteSelectedItems = React.useCallback(async () => {
    if (selectionKind === "tasks") {
      await Promise.all(
        Array.from(selectedTaskIds).map((taskId) =>
          Promise.resolve(handlers.onDeleteTask(taskId)),
        ),
      );
      setSelectedTaskIds(new Set());
    }

    if (selectionKind === "projects" && handlers.onDeleteProject) {
      for (const projectId of selectedProjectIds) {
        await handlers.onDeleteProject(projectId);
      }
      setSelectedProjectIds(new Set());
    }

    cancelSelectionMode();
  }, [
    selectedTaskIds,
    selectedProjectIds,
    handlers,
    cancelSelectionMode,
    selectionKind,
  ]);

  const selectedCount =
    selectionKind === "tasks"
      ? selectedTaskIds.size
      : selectionKind === "projects"
        ? selectedProjectIds.size
        : 0;

  return {
    selectionKind,
    isSelectionMode: selectionKind !== null,
    isTaskSelectionMode: selectionKind === "tasks",
    isProjectSelectionMode: selectionKind === "projects",
    selectedTaskIds,
    selectedProjectIds,
    selectedCount,
    enterTaskSelectionMode,
    enterProjectSelectionMode,
    enableTaskSelectionMode,
    toggleTaskSelection,
    enableProjectSelectionMode,
    toggleProjectSelection,
    cancelSelectionMode,
    deleteSelectedItems,
  };
}
