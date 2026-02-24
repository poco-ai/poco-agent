"use client";

import { useState, useCallback, useEffect } from "react";
import {
  createProjectAction,
  deleteProjectAction,
  listProjectsAction,
  updateProjectAction,
} from "@/features/projects/actions/project-actions";
import type { ProjectItem } from "@/features/projects/types";
import {
  getStartupPreloadPromise,
  getStartupPreloadValue,
  hasStartupPreloadValue,
} from "@/lib/startup-preload";
import type {
  ProjectRepoDefaultsInput,
  ProjectUpdatesInput,
} from "@/components/shell/app-shell-context";

interface UseProjectsOptions {
  initialProjects?: ProjectItem[];
  enableClientFetch?: boolean;
}

export function useProjects(options: UseProjectsOptions = {}) {
  const preloadProjects = getStartupPreloadValue("projects");
  const hasPreloadedProjects = hasStartupPreloadValue("projects");
  const { initialProjects = [] } = options;
  const seededProjects = hasPreloadedProjects
    ? (preloadProjects ?? [])
    : initialProjects;
  const enableClientFetch =
    options.enableClientFetch ??
    (!hasPreloadedProjects && initialProjects.length === 0);
  const [projects, setProjects] = useState<ProjectItem[]>(seededProjects);
  const [isLoading, setIsLoading] = useState(enableClientFetch);

  const fetchProjects = useCallback(async () => {
    try {
      setIsLoading(true);
      if (hasStartupPreloadValue("projects")) {
        setProjects(getStartupPreloadValue("projects") ?? []);
        return;
      }

      const preloadPromise = getStartupPreloadPromise();
      if (preloadPromise) {
        await preloadPromise;
        if (hasStartupPreloadValue("projects")) {
          setProjects(getStartupPreloadValue("projects") ?? []);
          return;
        }
      }

      const data = await listProjectsAction();
      setProjects(data);
    } catch (error) {
      console.error("Failed to fetch projects", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enableClientFetch) {
      setIsLoading(false);
      return;
    }
    fetchProjects();
  }, [enableClientFetch, fetchProjects]);

  const addProject = useCallback(
    async (name: string, options?: ProjectRepoDefaultsInput) => {
      try {
        const newProject = await createProjectAction({
          name,
          ...(options ?? {}),
        });
        setProjects((prev) => [...prev, newProject]);
        return newProject;
      } catch (error) {
        console.error("Failed to create project", error);
        return null;
      }
    },
    [],
  );

  const updateProject = useCallback(
    async (projectId: string, updates: ProjectUpdatesInput) => {
      try {
        const updated = await updateProjectAction({
          projectId,
          ...updates,
        });
        setProjects((prev) =>
          prev.map((project) =>
            project.id === projectId ? { ...project, ...updated } : project,
          ),
        );
        return updated;
      } catch (error) {
        console.error("Failed to update project", error);
        return null;
      }
    },
    [],
  );

  const removeProject = useCallback(
    async (projectId: string) => {
      const previousProjects = projects;
      setProjects((prev) => prev.filter((project) => project.id !== projectId));
      try {
        await deleteProjectAction({ projectId });
      } catch (error) {
        console.error("Failed to delete project", error);
        setProjects(previousProjects);
      }
    },
    [projects],
  );

  return {
    projects,
    isLoading,
    addProject,
    updateProject,
    removeProject,
    refreshProjects: fetchProjects,
  };
}
