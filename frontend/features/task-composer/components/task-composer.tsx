import * as React from "react";
import { Upload } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ScheduledTaskSettingsDialog } from "@/features/scheduled-tasks/components/scheduled-task-settings-dialog";
import {
  formatScheduleSummary,
  inferScheduleFromCron,
} from "@/features/scheduled-tasks/utils/schedule";
import { RunScheduleDialog } from "@/features/task-composer/components/run-schedule-dialog";
import { ComposerAttachments } from "@/features/task-composer/components/composer-attachments";
import { CapabilityRecommendations } from "@/features/task-composer/components/capability-recommendations";
import { ComposerToolbar } from "@/features/task-composer/components/composer-toolbar";
import { RepoDialog } from "@/features/task-composer/components/repo-dialog";
import { SlashAutocompleteDropdown } from "@/features/task-composer/components/slash-autocomplete-dropdown";
import { useCapabilityRecommendations } from "@/features/task-composer/hooks/use-capability-recommendations";
import { getNextComposerMode } from "@/features/task-composer/lib/mode-utils";
import { useSlashCommandAutocomplete } from "@/features/chat/hooks/use-slash-command-autocomplete";
import { useAppShell } from "@/components/shell/app-shell-context";
import { useMemoryFeatureEnabled } from "@/hooks/use-memory-feature-enabled";
import { useFileDropUpload } from "@/features/task-composer/hooks/use-file-drop-upload";
import { useFileUpload } from "@/features/task-composer/hooks/use-file-upload";
import { appendTranscribedText, useVoiceInput } from "@/features/voice";
import { playInstallSound } from "@/lib/utils/sound";
import { useCapabilityToggle } from "@/features/connectors";
import type { RunScheduleMode } from "@/features/task-composer/model/run-schedule";
import type {
  ComposerMode,
  RepoUsageMode,
  TaskSendOptions,
} from "@/features/task-composer/types";
import type { CapabilityRecommendation } from "@/features/task-composer/types/capability-recommendation";

interface TrackedCapabilityItem {
  item: CapabilityRecommendation;
  restoreEnabled: boolean;
}

function toCapabilityToggleConfig(
  toggles: Record<string, boolean> | Record<number, boolean> | null | undefined,
): Record<string, boolean> {
  const result: Record<string, boolean> = {};
  if (!toggles) {
    return result;
  }

  for (const [key, value] of Object.entries(toggles)) {
    if (typeof value === "boolean") {
      result[key] = value;
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TaskComposerProps {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  mode: ComposerMode;
  onModeChange: (mode: ComposerMode) => void;
  onSend: (options?: TaskSendOptions) => void | Promise<void>;
  isSubmitting?: boolean;
  allowProjectize?: boolean;
  onRepoDefaultsSave?: (payload: {
    repo_url: string;
    git_branch: string | null;
    git_token_env_key: string | null;
  }) => void | Promise<void>;
  bottomAddon?: React.ReactNode;
  onFocus?: () => void;
  onBlur?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Task composition area with file upload, repo config, scheduling, and
 * slash-command autocomplete.
 *
 * This component orchestrates several sub-components:
 * - `ComposerAttachments` – displays attached files and repo card
 * - `RepoDialog` – GitHub repo configuration
 * - `SlashAutocompleteDropdown` – slash-command suggestions
 * - `ComposerToolbar` – bottom action buttons
 */
export function TaskComposer({
  textareaRef,
  value,
  onChange,
  mode,
  onModeChange,
  onSend,
  isSubmitting,
  allowProjectize = true,
  onRepoDefaultsSave,
  bottomAddon,
  onFocus,
  onBlur,
}: TaskComposerProps) {
  const { t } = useT("translation");
  const { lng } = useAppShell();
  const memoryFeatureEnabled = useMemoryFeatureEnabled();
  const capabilityToggle = useCapabilityToggle();
  const isComposing = React.useRef(false);
  const memoryInitializedRef = React.useRef(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const latestValueRef = React.useRef(value);
  const trackedCapabilityItemsRef = React.useRef<TrackedCapabilityItem[]>([]);

  React.useEffect(() => {
    latestValueRef.current = value;
  }, [value]);

  // ---- File upload (shared hook) ----
  const upload = useFileUpload({ t });
  const fileDrop = useFileDropUpload({
    disabled: Boolean(isSubmitting) || upload.isUploading,
    onFilesDrop: upload.uploadFiles,
  });

  // ---- Slash-command autocomplete ----
  const slashAutocomplete = useSlashCommandAutocomplete({
    value,
    onChange,
    textareaRef,
  });
  const voiceInput = useVoiceInput({
    t,
    language: lng,
    onTranscription: React.useCallback(
      (text: string) => {
        const nextValue = appendTranscribedText(latestValueRef.current, text);
        onChange(nextValue);

        requestAnimationFrame(() => {
          const textarea = textareaRef.current;
          if (!textarea) return;
          textarea.focus();
          textarea.setSelectionRange(nextValue.length, nextValue.length);
        });
      },
      [onChange, textareaRef],
    ),
  });

  // ---- Browser toggle ----
  const [browserEnabled, setBrowserEnabled] = React.useState(true);
  const [memoryEnabled, setMemoryEnabled] =
    React.useState(memoryFeatureEnabled);
  const [trackedCapabilityItems, setTrackedCapabilityItems] = React.useState<
    TrackedCapabilityItem[]
  >([]);

  const effectiveMcpConfig = React.useMemo(
    () => toCapabilityToggleConfig(capabilityToggle?.mcpEnabledMap),
    [capabilityToggle],
  );

  const effectiveSkillConfig = React.useMemo(
    () => toCapabilityToggleConfig(capabilityToggle?.skillEnabledMap),
    [capabilityToggle],
  );

  // ---- Repo state ----
  const [repoDialogOpen, setRepoDialogOpen] = React.useState(false);
  const [repoUrl, setRepoUrl] = React.useState("");
  const [gitBranch, setGitBranch] = React.useState("main");
  const [gitTokenEnvKey, setGitTokenEnvKey] = React.useState("");
  const [repoUsage, setRepoUsage] = React.useState<RepoUsageMode>("session");
  const [projectName, setProjectName] = React.useState("");

  // ---- Run schedule state ----
  const [runScheduleOpen, setRunScheduleOpen] = React.useState(false);
  const [runScheduleMode, setRunScheduleMode] =
    React.useState<RunScheduleMode>("immediate");
  const [runScheduledAt, setRunScheduledAt] = React.useState<string | null>(
    null,
  );
  const [runTimezone, setRunTimezone] = React.useState("UTC");

  // ---- Scheduled task state ----
  const [scheduledSettingsOpen, setScheduledSettingsOpen] =
    React.useState(false);
  const [scheduledName, setScheduledName] = React.useState("");
  const [scheduledCron, setScheduledCron] = React.useState("*/5 * * * *");
  const [scheduledTimezone, setScheduledTimezone] = React.useState("UTC");
  const [scheduledEnabled, setScheduledEnabled] = React.useState(true);
  const [scheduledReuseSession, setScheduledReuseSession] =
    React.useState(true);

  const capabilityRecommendations = useCapabilityRecommendations(value, {
    enabled: !isSubmitting,
    limit: 3,
  });
  const showRecommendationEmptyState =
    capabilityRecommendations.hasFetched &&
    value.trim().length >= capabilityRecommendations.minQueryLength;
  const hasInput = value.trim().length > 0;
  const showRecommendationsInFooter =
    hasInput &&
    (capabilityRecommendations.isLoading ||
      capabilityRecommendations.items.length > 0 ||
      trackedCapabilityItems.length > 0 ||
      showRecommendationEmptyState);

  // ---- Derived values ----
  const firstLine =
    mode === "scheduled"
      ? t("library.scheduledTasks.placeholders.prompt")
      : mode === "plan"
        ? t("hero.inputPrompts.planDefault")
        : t("hero.inputPrompts.taskDefault");
  const placeholderText = firstLine;

  const scheduledSummary = React.useMemo(() => {
    const inferred = inferScheduleFromCron(scheduledCron);
    return formatScheduleSummary(inferred, t);
  }, [scheduledCron, t]);

  // ---- Effects ----

  // Auto-detect timezone
  React.useEffect(() => {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (tz) {
        setScheduledTimezone(tz);
        setRunTimezone(tz);
      }
    } catch {
      // Keep UTC as fallback
    }
  }, []);

  React.useEffect(() => {
    if (!memoryFeatureEnabled) {
      setMemoryEnabled(false);
      memoryInitializedRef.current = false;
      return;
    }

    if (memoryInitializedRef.current) return;
    setMemoryEnabled(true);
    memoryInitializedRef.current = true;
  }, [memoryFeatureEnabled]);

  React.useEffect(() => {
    trackedCapabilityItemsRef.current = trackedCapabilityItems;
  }, [trackedCapabilityItems]);

  // Reset capability recommendation state when input is cleared
  React.useEffect(() => {
    if (value.trim().length > 0) return;
    const prev = trackedCapabilityItemsRef.current;
    for (const entry of prev) {
      if (entry.item.type === "mcp") {
        capabilityToggle?.toggleMcp(entry.item.id, entry.restoreEnabled);
      } else {
        capabilityToggle?.toggleSkill(entry.item.id, entry.restoreEnabled);
      }
    }
    setTrackedCapabilityItems([]);
  }, [value, capabilityToggle]);

  // Default scheduled name from input
  React.useEffect(() => {
    if (mode !== "scheduled" || scheduledName.trim()) return;
    const derived = value.trim().slice(0, 32);
    if (derived) setScheduledName(derived);
  }, [mode, scheduledName, value]);

  // ---- Handlers ----

  const handleRepoSave = React.useCallback(async () => {
    if (isSubmitting || upload.isUploading) return;
    const url = repoUrl.trim();
    if (url && onRepoDefaultsSave) {
      try {
        await onRepoDefaultsSave({
          repo_url: url,
          git_branch: gitBranch.trim() || null,
          git_token_env_key: gitTokenEnvKey.trim() || null,
        });
      } catch (error) {
        console.error("[TaskComposer] Failed to persist repo defaults", error);
      }
    }
    setRepoDialogOpen(false);
  }, [
    gitBranch,
    gitTokenEnvKey,
    isSubmitting,
    upload.isUploading,
    onRepoDefaultsSave,
    repoUrl,
  ]);

  const canSubmit = React.useMemo(() => {
    if (mode === "scheduled") {
      return Boolean(value.trim()) && Boolean(scheduledCron.trim());
    }
    const hasContent = Boolean(value.trim()) || upload.attachments.length > 0;
    if (runScheduleMode === "scheduled" && !(runScheduledAt || "").trim()) {
      return false;
    }
    return hasContent;
  }, [
    mode,
    value,
    scheduledCron,
    upload.attachments.length,
    runScheduleMode,
    runScheduledAt,
  ]);

  const handleSubmit = React.useCallback(() => {
    if (isSubmitting || upload.isUploading || voiceInput.isBusy || !canSubmit) {
      return;
    }

    const payload: TaskSendOptions = {
      attachments: upload.attachments,
      repo_url: repoUrl.trim() || null,
      git_branch: gitBranch.trim() || null,
      git_token_env_key: repoUrl.trim() ? gitTokenEnvKey.trim() || null : null,
      repo_usage: allowProjectize ? repoUsage : null,
      project_name:
        allowProjectize && repoUsage === "create_project"
          ? projectName.trim() || null
          : null,
      browser_enabled: browserEnabled,
      memory_enabled: memoryFeatureEnabled ? memoryEnabled : false,
      mcp_config:
        Object.keys(effectiveMcpConfig).length > 0 ? effectiveMcpConfig : null,
      skill_config:
        Object.keys(effectiveSkillConfig).length > 0
          ? effectiveSkillConfig
          : null,
      run_schedule:
        mode === "scheduled"
          ? null
          : {
              schedule_mode: runScheduleMode,
              timezone: runTimezone.trim() || "UTC",
              scheduled_at:
                runScheduleMode === "scheduled"
                  ? (runScheduledAt || "").trim()
                  : null,
            },
      scheduled_task:
        mode === "scheduled"
          ? {
              name: (scheduledName.trim() || value.trim().slice(0, 32)).trim(),
              cron: scheduledCron.trim(),
              timezone: scheduledTimezone.trim() || "UTC",
              enabled: scheduledEnabled,
              reuse_session: scheduledReuseSession,
            }
          : null,
    };

    onSend(payload);
    upload.clearAttachments();
    setRunScheduleMode("immediate");
    setRunScheduledAt(null);
  }, [
    allowProjectize,
    browserEnabled,
    effectiveMcpConfig,
    effectiveSkillConfig,
    canSubmit,
    gitBranch,
    gitTokenEnvKey,
    isSubmitting,
    memoryEnabled,
    memoryFeatureEnabled,
    mode,
    onSend,
    projectName,
    repoUrl,
    repoUsage,
    runScheduleMode,
    runScheduledAt,
    runTimezone,
    scheduledCron,
    scheduledEnabled,
    scheduledName,
    scheduledReuseSession,
    scheduledTimezone,
    upload,
    value,
    voiceInput.isBusy,
  ]);

  const isCapabilityEnabled = React.useCallback(
    (item: CapabilityRecommendation) => {
      const key = String(item.id);
      const override =
        item.type === "mcp"
          ? effectiveMcpConfig[key]
          : effectiveSkillConfig[key];
      return typeof override === "boolean" ? override : item.default_enabled;
    },
    [effectiveMcpConfig, effectiveSkillConfig],
  );

  const handleToggleCapability = React.useCallback(
    (item: CapabilityRecommendation, enabled: boolean) => {
      const key = String(item.id);
      const currentEnabled =
        item.type === "mcp"
          ? effectiveMcpConfig[key]
          : effectiveSkillConfig[key];
      const restoreEnabled =
        typeof currentEnabled === "boolean"
          ? currentEnabled
          : item.default_enabled;

      if (item.type === "mcp") {
        capabilityToggle?.toggleMcp(item.id, enabled);
      } else {
        capabilityToggle?.toggleSkill(item.id, enabled);
      }

      if (enabled) {
        playInstallSound();
      }

      setTrackedCapabilityItems((prev) => {
        const existingIndex = prev.findIndex(
          (entry) => entry.item.type === item.type && entry.item.id === item.id,
        );

        if (existingIndex !== -1) {
          const existing = prev[existingIndex];
          if (enabled === existing.restoreEnabled) {
            return prev.filter((_, index) => index !== existingIndex);
          }
          return prev.map((entry, index) =>
            index === existingIndex ? { ...entry, item } : entry,
          );
        }

        if (enabled === restoreEnabled) {
          return prev;
        }

        return [...prev, { item, restoreEnabled }];
      });
    },
    [capabilityToggle, effectiveMcpConfig, effectiveSkillConfig],
  );

  // ---- Render ----
  return (
    <>
      <div
        className="relative rounded-2xl border border-border bg-card shadow-sm"
        data-onboarding="home-task-composer"
      >
        {/* Hidden file input */}
        <input
          type="file"
          multiple
          ref={fileInputRef}
          className="hidden"
          onChange={upload.handleFileSelect}
        />

        {/* Attachments */}
        <ComposerAttachments
          repoUrl={repoUrl}
          gitBranch={gitBranch}
          attachments={upload.attachments}
          onOpenRepoDialog={() => setRepoDialogOpen(true)}
          onRemoveRepo={() => setRepoUrl("")}
          onRemoveAttachment={upload.removeAttachment}
        />

        {/* Repo dialog */}
        <RepoDialog
          open={repoDialogOpen}
          onOpenChange={setRepoDialogOpen}
          mode={mode}
          allowProjectize={allowProjectize}
          lng={lng}
          repoUrl={repoUrl}
          onRepoUrlChange={setRepoUrl}
          gitBranch={gitBranch}
          onGitBranchChange={setGitBranch}
          gitTokenEnvKey={gitTokenEnvKey}
          onGitTokenEnvKeyChange={setGitTokenEnvKey}
          repoUsage={repoUsage}
          onRepoUsageChange={setRepoUsage}
          projectName={projectName}
          onProjectNameChange={setProjectName}
          onSave={handleRepoSave}
        />

        {/* Scheduled task settings */}
        <ScheduledTaskSettingsDialog
          open={scheduledSettingsOpen}
          onOpenChange={setScheduledSettingsOpen}
          value={{
            name: scheduledName,
            cron: scheduledCron,
            timezone: scheduledTimezone,
            enabled: scheduledEnabled,
            reuse_session: scheduledReuseSession,
          }}
          onSave={(next) => {
            setScheduledName(next.name);
            setScheduledCron(next.cron);
            setScheduledTimezone(next.timezone);
            setScheduledEnabled(next.enabled);
            setScheduledReuseSession(next.reuse_session);
          }}
        />

        {/* Run schedule dialog */}
        <RunScheduleDialog
          open={runScheduleOpen}
          onOpenChange={setRunScheduleOpen}
          value={{
            schedule_mode: runScheduleMode,
            timezone: runTimezone,
            scheduled_at: runScheduledAt,
          }}
          onSave={(next) => {
            setRunScheduleMode(next.schedule_mode);
            setRunTimezone(next.timezone);
            setRunScheduledAt(next.scheduled_at);
          }}
        />

        {/* Textarea with slash autocomplete */}
        <div className="relative px-4 pb-3 pt-4">
          <SlashAutocompleteDropdown
            isOpen={slashAutocomplete.isOpen}
            suggestions={slashAutocomplete.suggestions}
            activeIndex={slashAutocomplete.activeIndex}
            onHover={slashAutocomplete.setActiveIndex}
            onSelect={slashAutocomplete.applySelection}
          />
          <Textarea
            ref={textareaRef}
            value={value}
            disabled={isSubmitting}
            onChange={(e) => onChange(e.target.value)}
            onCompositionStart={() => (isComposing.current = true)}
            onCompositionEnd={() => {
              requestAnimationFrame(() => {
                isComposing.current = false;
              });
            }}
            onPaste={upload.handlePaste}
            onFocus={onFocus}
            onBlur={onBlur}
            onKeyDown={(e) => {
              if (e.shiftKey && e.key === "Tab") {
                e.preventDefault();
                e.stopPropagation();
                onModeChange(getNextComposerMode(mode));
                return;
              }
              if (slashAutocomplete.handleKeyDown(e)) return;
              if (e.key === "Enter") {
                if (e.shiftKey) return;
                if (
                  e.nativeEvent.isComposing ||
                  isComposing.current ||
                  e.keyCode === 229
                ) {
                  return;
                }
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder={placeholderText}
            className={cn(
              "min-h-[60px] max-h-[40vh] w-full resize-none border-0 bg-transparent dark:bg-transparent p-0 text-base shadow-none placeholder:text-muted-foreground/50 focus-visible:ring-0 disabled:opacity-50",
            )}
            rows={2}
          />
        </div>

        {/* Bottom toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 pb-4">
          <div className="flex-1 min-w-0">
            <ComposerToolbar
              mode={mode}
              onModeChange={onModeChange}
              isSubmitting={isSubmitting}
              isUploading={upload.isUploading}
              canSubmit={canSubmit}
              hasVoiceSupport={voiceInput.isSupported}
              voiceStatus={voiceInput.status}
              browserEnabled={browserEnabled}
              memoryFeatureEnabled={memoryFeatureEnabled}
              memoryEnabled={memoryEnabled}
              onOpenRepoDialog={() => setRepoDialogOpen(true)}
              onBrowserEnabledChange={setBrowserEnabled}
              onMemoryEnabledChange={setMemoryEnabled}
              onOpenFileInput={() => fileInputRef.current?.click()}
              onToggleVoiceInput={() => {
                void voiceInput.toggleRecording();
              }}
              onSubmit={handleSubmit}
              scheduledSummary={
                mode === "scheduled" ? scheduledSummary : undefined
              }
              onOpenScheduledSettings={
                mode === "scheduled"
                  ? () => setScheduledSettingsOpen(true)
                  : undefined
              }
            />
          </div>
        </div>

        {bottomAddon ? (
          <div className="border-t border-border/60">{bottomAddon}</div>
        ) : null}
      </div>

      {showRecommendationsInFooter ? (
        <div className="mt-3">
          <CapabilityRecommendations
            recommendations={capabilityRecommendations.items}
            trackedItems={trackedCapabilityItems.map((entry) => entry.item)}
            isLoading={capabilityRecommendations.isLoading}
            showEmptyState={showRecommendationEmptyState}
            isEnabled={isCapabilityEnabled}
            onToggle={handleToggleCapability}
            footerMode
          />
        </div>
      ) : null}

      {fileDrop.isDragActive ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-sm">
          <div className="mx-4 flex w-full max-w-xl flex-col items-center justify-center rounded-2xl border-2 border-dashed border-primary/60 bg-card/95 px-8 py-10 text-center shadow-xl">
            <Upload className="mb-4 size-6 text-primary" />
            <p className="text-base font-medium text-foreground">
              {t("hero.dragDrop.title")}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {t("hero.dragDrop.hint")}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("hero.dragDrop.escHint")}
            </p>
          </div>
        </div>
      ) : null}
    </>
  );
}
