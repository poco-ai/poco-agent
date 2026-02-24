import { useCallback } from "react";

interface UseProjectActionsOptions {
  updateProject: (
    projectId: string,
    updates: { name: string },
  ) => Promise<unknown>;
  deleteProject: (projectId: string) => Promise<void>;
}

interface UseProjectActionsResult {
  handleRenameProject: (projectId: string, newName: string) => void;
  handleDeleteProject: (projectId: string) => Promise<void>;
}

/**
 * Hook to create stable callbacks for project rename and delete actions.
 */
export function useProjectActions({
  updateProject,
  deleteProject,
}: UseProjectActionsOptions): UseProjectActionsResult {
  const handleRenameProject = useCallback(
    (projectId: string, newName: string) => {
      updateProject(projectId, { name: newName });
    },
    [updateProject],
  );

  const handleDeleteProject = useCallback(
    async (projectId: string) => {
      await deleteProject(projectId);
    },
    [deleteProject],
  );

  return {
    handleRenameProject,
    handleDeleteProject,
  };
}
