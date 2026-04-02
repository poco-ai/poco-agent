"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FolderSearch } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";

import {
  type ComposerMode,
  type LocalFilesystemDraft,
  type TaskSendOptions,
  submitScheduledTask,
  submitTask,
  useAutosizeTextarea,
} from "@/features/task-composer";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";

import { ProjectDetailPanel } from "@/features/projects/components/project-detail-panel";
import { ProjectHeader } from "@/features/projects/components/project-header";
import { ProjectInfoDrawer } from "@/features/projects/components/project-info-drawer";
import { ProjectSettingsDialog } from "@/features/projects/components/project-settings-dialog";
import { CapabilityToggleProvider } from "@/features/connectors";
import { useAppShell } from "@/components/shell/app-shell-context";
import { cn } from "@/lib/utils";
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
    () => projects.find((p: ProjectItem) => p.id === projectId),
    [projects, projectId],
  );

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [mode, setMode] = React.useState<ComposerMode>("task");
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = React.useState(true);
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
  const defaultPresetId = currentProject?.defaultPresetId ?? null;

  const projectModelSelection = React.useMemo<ModelSelection | null>(() => {
    const modelId = (currentProject?.defaultModel || "").trim();
    if (!modelId) {
      return null;
    }
    return {
      modelId,
      providerId: null,
    };
  }, [currentProject?.defaultModel]);

  const projectFilesystemDraft = React.useMemo<LocalFilesystemDraft>(() => {
    if (!currentProject?.localMounts?.length) {
      return {
        filesystem_mode: "sandbox",
        local_mounts: [],
      };
    }

    return {
      filesystem_mode: "local_mount",
      local_mounts: currentProject.localMounts.map((mount) => ({
        ...mount,
        access_mode: mount.access_mode ?? "ro",
      })),
    };
  }, [currentProject?.localMounts]);

  const handleSaveProjectFilesystemDraft = React.useCallback(
    async (nextValue: LocalFilesystemDraft) => {
      await updateProject(projectId, {
        local_mounts: nextValue.local_mounts,
      });
    },
    [projectId, updateProject],
  );

  const handleSendTask = React.useCallback(
    async (options?: TaskSendOptions) => {
      const inputFiles = options?.attachments ?? [];
      const repoUrl = (options?.repo_url || "").trim();
      const gitBranch = (options?.git_branch || "").trim() || "main";
      const gitTokenEnvKey = (options?.git_token_env_key || "").trim();
      const runSchedule = options?.run_schedule ?? null;
      const scheduledTask = options?.scheduled_task ?? null;
      const effectiveFilesystemMode =
        options?.filesystem_mode ??
        (currentProject?.localMounts?.length
          ? projectFilesystemDraft.filesystem_mode
          : null);
      const effectiveLocalMounts =
        options?.local_mounts && options.local_mounts.length > 0
          ? options.local_mounts
          : currentProject?.localMounts?.length
            ? projectFilesystemDraft.local_mounts
            : null;
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
            options: {
              ...options,
              filesystem_mode: effectiveFilesystemMode,
              local_mounts: effectiveLocalMounts,
            },
            selectedModel: projectModelSelection,
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
              filesystem_mode: effectiveFilesystemMode,
              local_mounts: effectiveLocalMounts,
              run_schedule: runSchedule,
              scheduled_task: scheduledTask,
            },
            selectedModel: projectModelSelection,
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
      projectFilesystemDraft.filesystem_mode,
      projectFilesystemDraft.local_mounts,
      projectModelSelection,
      router,
      t,
      updateProject,
      currentProject?.localMounts,
    ],
  );

  const toggleDrawer = React.useCallback(() => {
    setIsDrawerOpen((prev) => !prev);
  }, []);

  return (
    <CapabilityToggleProvider>
      <div className="flex min-h-0 flex-1 flex-col bg-background">
        {currentProject ? (
          <div
            className="grid min-h-0 flex-1 overflow-hidden transition-[grid-template-columns] duration-200 ease-linear"
            style={{
              gridTemplateColumns: isDrawerOpen
                ? "18rem minmax(0, 1fr)"
                : "0px minmax(0, 1fr)",
              gridTemplateRows: "3.5rem minmax(0, 1fr)",
            }}
          >
            <div
              className={cn(
                "row-span-2 min-h-0 overflow-hidden bg-background transition-[border-color] duration-200",
                isDrawerOpen
                  ? "border-r border-border/60"
                  : "border-r border-transparent",
              )}
            >
              <div
                className={cn(
                  "flex h-full w-72 flex-col transition-opacity duration-150",
                  isDrawerOpen
                    ? "opacity-100"
                    : "pointer-events-none opacity-0",
                )}
                aria-hidden={!isDrawerOpen}
              >
                <ProjectHeader
                  project={currentProject}
                  isDrawerOpen
                  onToggleDrawer={toggleDrawer}
                  onOpenSettings={() => setSettingsOpen(true)}
                />
                <div className="min-h-0 flex-1 overflow-hidden">
                  <ProjectInfoDrawer
                    project={currentProject}
                    sessionCount={projectTasks.length}
                    presetCount={currentProject.defaultPresetId ? 1 : 0}
                    onUpdateProject={async (updates) => {
                      await updateProject(projectId, {
                        name: updates.name,
                        description: updates.description,
                        default_model: updates.defaultModel,
                        local_mounts: updates.localMounts,
                      });
                    }}
                    onOpenSettings={() => setSettingsOpen(true)}
                    onDeleteProject={async () => {
                      await deleteProject(projectId);
                      router.push(homePath);
                    }}
                  />
                </div>
              </div>
            </div>
            <div className="min-w-0 bg-background">
              {isDrawerOpen ? (
                <div className="h-14 min-h-14 bg-background" />
              ) : (
                <ProjectHeader
                  project={currentProject}
                  isDrawerOpen={false}
                  onToggleDrawer={toggleDrawer}
                  onOpenSettings={() => setSettingsOpen(true)}
                />
              )}
            </div>
            <div className="flex min-h-0 min-w-0 flex-col bg-background">
              <ProjectDetailPanel
                projectTitle={projectTitle}
                mode={mode}
                onModeChange={setMode}
                textareaRef={textareaRef}
                inputValue={inputValue}
                onInputChange={setInputValue}
                onSendTask={handleSendTask}
                isSubmitting={isSubmitting}
                initialPresetId={defaultPresetId}
                initialLocalFilesystemDraft={projectFilesystemDraft}
                onLocalFilesystemDraftSave={handleSaveProjectFilesystemDraft}
                onRepoDefaultsSave={async (payload) => {
                  await updateProject(projectId, payload);
                }}
              />
            </div>
          </div>
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
              <Button className="mt-6" onClick={() => router.push(homePath)}>
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
            projectDefaultPresetId={currentProject.defaultPresetId ?? null}
            onProjectDefaultPresetChange={async (presetId) => {
              const updatedProject = await updateProject(projectId, {
                default_preset_id: presetId,
              });
              if (!updatedProject) {
                throw new Error("Failed to persist project default preset");
              }
            }}
          />
        ) : null}
      </div>
    </CapabilityToggleProvider>
  );
}
