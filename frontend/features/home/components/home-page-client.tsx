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
import type { ModelConfigResponse } from "@/features/chat/types";

import { HomeHeader } from "./home-header";
import { ConnectorsBar } from "@/features/connectors";

import { useAppShell } from "@/components/shared/app-shell-context";
import { toast } from "sonner";
import { modelConfigService } from "@/features/home/services/model-config-service";

const MODEL_STORAGE_KEY = "poco_selected_model";

export function HomePageClient() {
  const { t } = useT("translation");
  const router = useRouter();
  const { lng, addTask, addProject, openSettings } = useAppShell();

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [isInputFocused, setIsInputFocused] = React.useState(false);
  const [mode, setMode] = React.useState<ComposerMode>("task");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const [modelConfig, setModelConfig] =
    React.useState<ModelConfigResponse | null>(null);
  const [selectedModel, setSelectedModel] = React.useState<string | null>(null);

  useAutosizeTextarea(textareaRef, inputValue);
  useComposerModeHotkeys({ textareaRef, setMode });

  React.useEffect(() => {
    let active = true;
    modelConfigService
      .get()
      .then((cfg) => {
        if (!active) return;
        setModelConfig(cfg);
      })
      .catch((error) => {
        console.error("[Home] Failed to load model config:", error);
      });
    return () => {
      active = false;
    };
  }, []);

  React.useEffect(() => {
    const defaultModel = (modelConfig?.default_model || "").trim();
    if (!defaultModel) return;

    let saved: string | null = null;
    try {
      saved = localStorage.getItem(MODEL_STORAGE_KEY);
    } catch {
      saved = null;
    }

    const cleaned = (saved || "").trim();
    if (!cleaned || cleaned === defaultModel) {
      setSelectedModel(null);
      return;
    }

    const allowed = new Set(
      (modelConfig?.model_list || [])
        .map((m) => (m || "").trim())
        .filter(Boolean),
    );
    setSelectedModel(allowed.has(cleaned) ? cleaned : null);
  }, [modelConfig]);

  const handleSelectModel = React.useCallback((model: string | null) => {
    const cleaned = (model || "").trim();
    const next = cleaned ? cleaned : null;
    setSelectedModel(next);
    try {
      if (!next) {
        localStorage.removeItem(MODEL_STORAGE_KEY);
      } else {
        localStorage.setItem(MODEL_STORAGE_KEY, next);
      }
    } catch {
      // Ignore storage failures (e.g., privacy mode).
    }
  }, []);

  // Determine if connectors bar should be expanded
  const shouldExpandConnectors = isInputFocused || inputValue.trim().length > 0;

  const handleSendTask = React.useCallback(
    async (options?: TaskSendOptions) => {
      const inputFiles = options?.attachments ?? [];
      const repoUrl = (options?.repo_url || "").trim();
      const gitBranch = (options?.git_branch || "").trim() || "main";
      const repoUsage = options?.repo_usage ?? null;
      const projectName = (options?.project_name || "").trim();
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
        if (mode === "scheduled") {
          const created = await submitScheduledTask({
            prompt: inputValue,
            mode,
            options,
            selectedModel,
          });

          toast.success(t("library.scheduledTasks.toasts.created"));
          setInputValue("");
          router.push(
            `/${lng}/capabilities/scheduled-tasks/${created.scheduledTaskId}`,
          );
          return;
        }

        let finalProjectId: string | undefined;
        if (repoUsage === "create_project") {
          if (!repoUrl) {
            toast.error(t("hero.repo.toasts.missingGithubUrl"));
            return;
          }

          const derived =
            (() => {
              try {
                const parsed = new URL(repoUrl);
                const host = parsed.hostname.toLowerCase();
                if (host !== "github.com" && host !== "www.github.com")
                  return "";
                const parts = parsed.pathname.split("/").filter(Boolean);
                if (parts.length < 2) return "";
                const owner = parts[0];
                let repo = parts[1];
                if (repo.endsWith(".git")) repo = repo.slice(0, -4);
                return owner && repo ? `${owner}/${repo}` : "";
              } catch {
                return "";
              }
            })() || repoUrl;

          const created = await addProject(projectName || derived, {
            repo_url: repoUrl,
            git_branch: gitBranch,
            git_token_env_key: gitTokenEnvKey || null,
          });
          if (!created) {
            toast.error(t("hero.repo.toasts.createProjectFailed"));
            return;
          }
          finalProjectId = created.id;
          toast.success(
            t("hero.repo.toasts.projectCreated", { name: created.name }),
          );
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
            selectedModel,
            projectId: finalProjectId,
          },
          { addTask },
        );
        const sessionId = session.sessionId;
        if (!sessionId) return;
        setInputValue("");
        router.push(`/${lng}/chat/${sessionId}`);
      } catch (error) {
        console.error("[Home] Failed to create session:", error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      addProject,
      addTask,
      inputValue,
      isSubmitting,
      lng,
      mode,
      router,
      selectedModel,
      t,
    ],
  );

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <HomeHeader
        onOpenSettings={openSettings}
        modelConfig={modelConfig}
        selectedModel={selectedModel}
        onSelectModel={handleSelectModel}
      />

      <TaskEntrySection
        title={t("hero.title")}
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
        }}
      />
    </div>
  );
}
