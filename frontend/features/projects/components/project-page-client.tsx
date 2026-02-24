"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { useT } from "@/lib/i18n/client";

import {
  TaskEntrySection,
  type ComposerMode,
  type TaskSendOptions,
  submitScheduledTask,
  submitTask,
  useAutosizeTextarea,
  useComposerModeHotkeys,
} from "@/features/task-composer";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";

import { ProjectHeader } from "@/features/projects/components/project-header";
import { ConnectorsBar } from "@/features/connectors";
import { useAppShell } from "@/components/shared/app-shell-context";
import { toast } from "sonner";

interface ProjectPageClientProps {
  projectId: string;
}

export function ProjectPageClient({ projectId }: ProjectPageClientProps) {
  const { t } = useT("translation");
  const router = useRouter();

  const { lng, projects, taskHistory, addTask, updateProject, deleteProject } =
    useAppShell();
  const currentProject = React.useMemo(
    () => projects.find((p: ProjectItem) => p.id === projectId) || projects[0],
    [projects, projectId],
  );

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const [mode, setMode] = React.useState<ComposerMode>("task");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  useAutosizeTextarea(textareaRef, inputValue);
  useComposerModeHotkeys({ textareaRef, setMode });

  const shouldExpandConnectors = isInputFocused || inputValue.trim().length > 0;

  const projectTaskCount = React.useMemo(
    () =>
      taskHistory.filter(
        (task: TaskHistoryItem) => task.projectId === projectId,
      ).length,
    [projectId, taskHistory],
  );

  const projectTitle = React.useMemo(() => {
    const baseName =
      currentProject?.name || t("project.untitled", "Untitled Project");
    return t("project.titleWithCount", {
      name: baseName,
      count: projectTaskCount,
    });
  }, [currentProject?.name, projectTaskCount, t]);

  const handleSendTask = React.useCallback(
    async (options?: TaskSendOptions) => {
      const inputFiles = options?.attachments ?? [];
      const repoUrl = (options?.repo_url || "").trim();
      const gitBranch = (options?.git_branch || "").trim() || "main";
      const gitTokenEnvKey = (options?.git_token_env_key || "").trim();
      const runSchedule = options?.run_schedule ?? null;
      const scheduledTask = options?.scheduled_task ?? null;
      if (
        (mode === "scheduled"
          ? inputValue.trim() === ""
          : inputValue.trim() === "" && inputFiles.length === 0) ||
        isSubmitting
      ) {
        return;
      }

      setIsSubmitting(true);

      try {
        // Best-effort: persist repo defaults on the project for future runs.
        if (repoUrl) {
          await updateProject(projectId, {
            repo_url: repoUrl,
            git_branch: gitBranch,
            ...(gitTokenEnvKey ? { git_token_env_key: gitTokenEnvKey } : {}),
          });
        }

        if (mode === "scheduled") {
          await submitScheduledTask({
            prompt: inputValue,
            mode,
            options,
            projectId,
          });
          toast.success(t("library.scheduledTasks.toasts.created"));
          setInputValue("");
          router.push(`/${lng}/capabilities/scheduled-tasks`);
          return;
        }

        const session = await submitTask(
          {
            prompt: inputValue,
            mode,
            options: {
              ...options,
              run_schedule: runSchedule,
              scheduled_task: scheduledTask,
            },
            projectId,
          },
          { addTask },
        );
        if (!session.sessionId) return;

        setInputValue("");
        router.push(`/${lng}/chat/${session.sessionId}`);
      } catch (error) {
        console.error("[Project] Failed to create session", error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      addTask,
      inputValue,
      isSubmitting,
      lng,
      mode,
      projectId,
      router,
      t,
      updateProject,
    ],
  );

  const handleRenameProject = React.useCallback(
    (targetProjectId: string, newName: string) => {
      updateProject(targetProjectId, { name: newName });
    },
    [updateProject],
  );

  const handleDeleteProject = React.useCallback(
    async (targetProjectId: string) => {
      await deleteProject(targetProjectId);
      if (targetProjectId === projectId) {
        router.push(`/${lng}/home`);
      }
    },
    [deleteProject, projectId, lng, router],
  );

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <ProjectHeader
        project={currentProject}
        onRenameProject={handleRenameProject}
        onDeleteProject={handleDeleteProject}
      />

      <TaskEntrySection
        title={projectTitle}
        mode={mode}
        onModeChange={setMode}
        toggleDisabled={isSubmitting}
        footer={<ConnectorsBar forceExpanded={shouldExpandConnectors} />}
        composerProps={{
          textareaRef,
          value: inputValue,
          onChange: setInputValue,
          onSend: handleSendTask,
          isSubmitting,
          onFocus: () => setIsInputFocused(true),
          onBlur: () => setIsInputFocused(false),
          allowProjectize: false,
          onRepoDefaultsSave: async (payload) => {
            await updateProject(projectId, payload);
          },
        }}
      />
    </div>
  );
}
