"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FolderSearch } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";

import {
  type ComposerMode,
  type TaskSendOptions,
  submitScheduledTask,
  submitTask,
  useAutosizeTextarea,
} from "@/features/task-composer";
import type { ProjectPreset } from "@/features/capabilities/presets";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";

import { ProjectDetailPanel } from "@/features/projects/components/project-detail-panel";
import { ProjectHeader } from "@/features/projects/components/project-header";
import { ProjectSettingsDialog } from "@/features/projects/components/project-settings-dialog";
import { getDefaultProjectPresetId } from "@/features/projects/lib/project-presets";
import { CapabilityToggleProvider } from "@/features/connectors";
import { useAppShell } from "@/components/shell/app-shell-context";
import { toast } from "sonner";
import { projectPresetsService } from "@/features/projects/api/project-presets-api";

interface ProjectPageClientProps {
  projectId: string;
}

export function ProjectPageClient({ projectId }: ProjectPageClientProps) {
  const { t } = useT("translation");
  const router = useRouter();

  const { lng, projects, taskHistory, addTask, updateProject, deleteProject } =
    useAppShell();
  const currentProject = React.useMemo(
    () => projects.find((p: ProjectItem) => p.id === projectId),
    [projects, projectId],
  );

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [mode, setMode] = React.useState<ComposerMode>("task");
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [projectPresets, setProjectPresets] = React.useState<ProjectPreset[]>(
    [],
  );
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  useAutosizeTextarea(textareaRef, inputValue);

  const projectTasks = React.useMemo(
    () =>
      taskHistory.filter(
        (task: TaskHistoryItem) => task.projectId === projectId,
      ),
    [projectId, taskHistory],
  );

  const projectTitle = React.useMemo(() => {
    return t("project.detail.composerTitle", {
      name: currentProject?.name || t("project.untitled", "Untitled Project"),
    });
  }, [currentProject?.name, t]);
  const homePath = lng ? `/${lng}/home` : "/home";

  React.useEffect(() => {
    let active = true;

    const loadProjectPresets = async () => {
      try {
        const items = await projectPresetsService.list(projectId, {
          revalidate: 0,
        });
        if (!active) return;
        setProjectPresets(items);
      } catch (error) {
        console.error("[ProjectPage] Failed to load project presets", error);
      }
    };

    void loadProjectPresets();
    return () => {
      active = false;
    };
  }, [projectId]);

  const defaultPresetId = React.useMemo(() => {
    return getDefaultProjectPresetId(projectPresets);
  }, [projectPresets]);

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
      void updateProject(targetProjectId, { name: newName });
    },
    [updateProject],
  );

  const handleDeleteProject = React.useCallback(
    async (targetProjectId: string) => {
      await deleteProject(targetProjectId);
      if (targetProjectId === projectId) {
        router.push(homePath);
      }
    },
    [deleteProject, homePath, projectId, router],
  );

  return (
    <CapabilityToggleProvider>
      <div className="flex min-h-0 flex-1 flex-col bg-background">
        <ProjectHeader
          project={currentProject}
          onOpenSettings={() => setSettingsOpen(true)}
          onRenameProject={handleRenameProject}
          onDeleteProject={handleDeleteProject}
        />

        {currentProject ? (
          <ProjectDetailPanel
            project={currentProject}
            projectTitle={projectTitle}
            projectTasks={projectTasks}
            projectPresets={projectPresets}
            mode={mode}
            onModeChange={setMode}
            onUpdateProject={async (updates) => {
              await updateProject(projectId, { name: updates.name });
            }}
            onOpenSettings={() => setSettingsOpen(true)}
            textareaRef={textareaRef}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSendTask={handleSendTask}
            isSubmitting={isSubmitting}
            initialPresetId={defaultPresetId}
            onRepoDefaultsSave={async (payload) => {
              await updateProject(projectId, payload);
            }}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
            <section className="w-full max-w-xl rounded-3xl border border-dashed border-border/70 bg-background px-6 py-10 text-center shadow-sm">
              <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-muted/50 text-muted-foreground">
                <FolderSearch className="size-7" />
              </div>
              <h1 className="mt-5 text-xl font-semibold text-foreground">
                {t("project.detail.notFoundTitle")}
              </h1>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {t("project.detail.notFoundDescription")}
              </p>
              <Button
                className="mt-6"
                onClick={() => router.push(homePath)}
              >
                {t("project.detail.backHome")}
              </Button>
            </section>
          </div>
        )}

        {currentProject ? (
          <ProjectSettingsDialog
            open={settingsOpen}
            onOpenChange={setSettingsOpen}
            projectId={projectId}
            projectName={currentProject.name}
            onProjectPresetsChange={setProjectPresets}
          />
        ) : null}
      </div>
    </CapabilityToggleProvider>
  );
}
