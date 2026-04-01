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
} from "@/features/task-composer";

import { HomeHeader } from "./home-header";
import { HomeBottomCardDeck } from "./home-bottom-card-deck";
import { HeroTitle } from "./hero-title";
import { ConnectorsBar, CapabilityToggleProvider } from "@/features/connectors";

import { useAppShell } from "@/components/shell/app-shell-context";
import { toast } from "sonner";
import { useModelCatalog } from "@/features/chat/hooks/use-model-catalog";
import {
  normalizeModelSelection,
  type ModelSelection,
} from "@/features/chat/lib/model-catalog";

const MODEL_STORAGE_KEY = "poco_selected_model";

function isSameSelection(
  left: ModelSelection | null | undefined,
  right: ModelSelection | null | undefined,
): boolean {
  return (
    (left?.modelId || "") === (right?.modelId || "") &&
    (left?.providerId || "") === (right?.providerId || "")
  );
}

export function HomePageClient() {
  const { t } = useT("translation");
  const router = useRouter();
  const { lng, addTask, addProject, openSettings } = useAppShell();

  const [inputValue, setInputValue] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [mode, setMode] = React.useState<ComposerMode>("task");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const [selectedModel, setSelectedModel] =
    React.useState<ModelSelection | null>(null);
  const { modelConfig, modelOptions } = useModelCatalog();
  const defaultOption = React.useMemo(
    () => modelOptions.find((option) => option.isDefault) ?? null,
    [modelOptions],
  );
  const availableOptionKeys = React.useMemo(
    () =>
      new Set(
        modelOptions
          .filter((option) => option.isAvailable)
          .map((option) => option.optionKey),
      ),
    [modelOptions],
  );

  useAutosizeTextarea(textareaRef, inputValue);

  React.useEffect(() => {
    const defaultModel = (modelConfig?.default_model || "").trim();
    if (!defaultModel) return;

    let saved: ModelSelection | null = null;
    try {
      const raw = localStorage.getItem(MODEL_STORAGE_KEY);
      saved = raw ? normalizeModelSelection(JSON.parse(raw)) : null;
    } catch {
      saved = null;
    }

    if (!saved?.modelId) {
      setSelectedModel((prev) => (prev ? null : prev));
      return;
    }

    const resolvedProviderId =
      saved.providerId ||
      modelOptions.find(
        (option) =>
          option.modelId === saved.modelId &&
          (saved.modelId !== defaultModel || option.isDefault),
      )?.providerId ||
      modelOptions.find((option) => option.modelId === saved.modelId)
        ?.providerId ||
      "";
    const normalizedSaved = {
      modelId: saved.modelId,
      providerId: resolvedProviderId || null,
    };
    const isDefaultSelection =
      normalizedSaved.modelId === (defaultOption?.modelId || "") &&
      (normalizedSaved.providerId || "") === (defaultOption?.providerId || "");
    if (isDefaultSelection) {
      setSelectedModel((prev) => (prev ? null : prev));
      return;
    }
    const selectionKey = `${resolvedProviderId}:${saved.modelId}`;
    if (!availableOptionKeys.has(selectionKey)) {
      try {
        localStorage.removeItem(MODEL_STORAGE_KEY);
      } catch {
        // Ignore storage failures (e.g., privacy mode).
      }
      setSelectedModel((prev) => (prev ? null : prev));
      return;
    }

    setSelectedModel((prev) =>
      isSameSelection(prev, normalizedSaved) ? prev : normalizedSaved,
    );
  }, [availableOptionKeys, defaultOption, modelConfig, modelOptions]);

  const handleSelectModel = React.useCallback(
    (selection: ModelSelection | null) => {
      const next = normalizeModelSelection(selection);
      const hasSelection = Boolean(next.modelId);
      setSelectedModel(hasSelection ? next : null);
      try {
        if (!hasSelection) {
          localStorage.removeItem(MODEL_STORAGE_KEY);
        } else {
          localStorage.setItem(MODEL_STORAGE_KEY, JSON.stringify(next));
        }
      } catch {
        // Ignore storage failures (e.g., privacy mode).
      }
    },
    [],
  );

  const handleFillSkillCreatorPrompt = React.useCallback(() => {
    const prompt = t("hero.skillCreatorCard.prefillPrompt");
    setInputValue(prompt);

    requestAnimationFrame(() => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      textarea.focus();
      textarea.setSelectionRange(prompt.length, prompt.length);
    });
  }, [t]);

  const bottomCards = React.useMemo(
    () => [
      {
        id: "skill-creator",
        title: t("hero.skillCreatorCard.title"),
        description: t("hero.skillCreatorCard.description"),
        onClick: handleFillSkillCreatorPrompt,
      },
    ],
    [handleFillSkillCreatorPrompt, t],
  );

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
    <CapabilityToggleProvider>
      <div className="flex flex-1 flex-col min-h-0">
        <HomeHeader
          onOpenSettings={openSettings}
          modelConfig={modelConfig}
          modelOptions={modelOptions}
          selectedModel={selectedModel}
          onSelectModel={handleSelectModel}
        />

        <TaskEntrySection
          title={<HeroTitle />}
          mode={mode}
          onModeChange={setMode}
          footer={<ConnectorsBar />}
          bottomPanel={<HomeBottomCardDeck cards={bottomCards} />}
          composerProps={{
            textareaRef,
            value: inputValue,
            onChange: setInputValue,
            onSend: handleSendTask,
            isSubmitting,
          }}
        />
      </div>
    </CapabilityToggleProvider>
  );
}
