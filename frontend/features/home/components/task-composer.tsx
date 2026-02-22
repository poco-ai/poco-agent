import * as React from "react";
import { useT } from "@/lib/i18n/client";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ScheduledTaskSettingsDialog } from "@/features/scheduled-tasks/components/scheduled-task-settings-dialog";
import {
  formatScheduleSummary,
  inferScheduleFromCron,
} from "@/features/scheduled-tasks/utils/schedule";
import {
  RunScheduleDialog,
  type RunScheduleMode,
} from "@/features/home/components/run-schedule-dialog";
import { useSlashCommandAutocomplete } from "@/features/chat/hooks/use-slash-command-autocomplete";
import { useAppShell } from "@/components/shared/app-shell-context";
import { useFileUpload } from "@/features/home/hooks/use-file-upload";
import type { InputFile } from "@/features/chat/types/api/session";

import { ComposerAttachments } from "./composer-attachments";
import { ComposerToolbar } from "./composer-toolbar";
import { RepoDialog } from "./repo-dialog";
import { SlashAutocompleteDropdown } from "./slash-autocomplete-dropdown";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type ComposerMode = "plan" | "task" | "scheduled";
export type RepoUsageMode = "session" | "create_project";

export interface TaskSendOptions {
  attachments?: InputFile[];
  repo_url?: string | null;
  git_branch?: string | null;
  git_token_env_key?: string | null;
  repo_usage?: RepoUsageMode | null;
  project_name?: string | null;
  browser_enabled?: boolean | null;
  run_schedule?: {
    schedule_mode: RunScheduleMode;
    timezone: string;
    scheduled_at: string | null;
  } | null;
  scheduled_task?: {
    name: string;
    cron: string;
    timezone: string;
    enabled: boolean;
    reuse_session: boolean;
  } | null;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TaskComposerProps {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  mode: ComposerMode;
  onSend: (options?: TaskSendOptions) => void | Promise<void>;
  isSubmitting?: boolean;
  allowProjectize?: boolean;
  onRepoDefaultsSave?: (payload: {
    repo_url: string;
    git_branch: string | null;
    git_token_env_key: string | null;
  }) => void | Promise<void>;
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
  onSend,
  isSubmitting,
  allowProjectize = true,
  onRepoDefaultsSave,
  onFocus,
  onBlur,
}: TaskComposerProps) {
  const { t } = useT("translation");
  const { lng } = useAppShell();
  const isComposing = React.useRef(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // ---- File upload (shared hook) ----
  const upload = useFileUpload({ t });

  // ---- Slash-command autocomplete ----
  const slashAutocomplete = useSlashCommandAutocomplete({
    value,
    onChange,
    textareaRef,
  });

  // ---- Browser toggle ----
  const [browserEnabled, setBrowserEnabled] = React.useState(false);

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
    if (isSubmitting || upload.isUploading || !canSubmit) return;

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
    canSubmit,
    gitBranch,
    gitTokenEnvKey,
    isSubmitting,
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
  ]);

  // ---- Render ----
  return (
    <div
      className="rounded-2xl border border-border bg-card shadow-sm"
      data-onboarding="home-task-composer"
    >
      {/* Hidden file input */}
      <input
        type="file"
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
          disabled={isSubmitting || upload.isUploading}
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
            isSubmitting={isSubmitting}
            isUploading={upload.isUploading}
            canSubmit={canSubmit}
            repoUrl={repoUrl}
            repoDialogOpen={repoDialogOpen}
            browserEnabled={browserEnabled}
            onOpenRepoDialog={() => setRepoDialogOpen(true)}
            onToggleBrowser={() => setBrowserEnabled((prev) => !prev)}
            onOpenFileInput={() => fileInputRef.current?.click()}
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
    </div>
  );
}
