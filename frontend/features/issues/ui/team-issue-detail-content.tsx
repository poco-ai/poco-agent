"use client";

import * as React from "react";
import Link from "next/link";
import { RefreshCw, Ticket, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { issuesApi } from "@/features/issues/api/issues-api";
import { getAssignmentExecutionMeta } from "@/features/issues/lib/issue-detail-view";
import {
  createIssueDetailFormData,
  shouldScheduleIssueDetailAutoSave,
  type IssueDetailFormData,
  type IssueDetailLoadState,
} from "@/features/issues/lib/issue-detail-form";
import {
  formatAssignmentStatus,
  formatIssueStatus,
} from "@/features/issues/lib/issue-presentation";
import type {
  AgentAssignment,
  WorkspaceIssue,
} from "@/features/issues/model/types";
import { projectsService } from "@/features/projects/api/projects-api";
import type { ProjectItem } from "@/features/projects/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return dateTimeFormatter.format(date);
}

const ACTION_TOAST_KEYS = {
  trigger: "issues.toasts.triggered",
  retry: "issues.toasts.retried",
  cancel: "issues.toasts.cancelled",
  release: "issues.toasts.released",
} as const;

function AssignmentBadge({
  assignment,
}: {
  assignment?: AgentAssignment | null;
}) {
  const { t } = useT("translation");
  if (!assignment) {
    return null;
  }
  return (
    <Badge variant="secondary">
      {formatAssignmentStatus(t, assignment.status)}
    </Badge>
  );
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  const { t } = useT("translation");
  return (
    <>
      <p className="text-sm font-medium">{label}</p>
      <p className={`mt-1 text-sm text-muted-foreground ${mono ? "break-all" : ""}`}>
        {value || t("issues.none")}
      </p>
    </>
  );
}

function FieldSelect({
  label,
  value,
  onValueChange,
  placeholder,
  children,
}: {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>{children}</SelectContent>
      </Select>
    </div>
  );
}

interface TeamIssueDetailContentProps {
  issueId: string;
  onDeleted: (issueId: string) => void;
  onUpdated: (issue: WorkspaceIssue) => void;
}

export function TeamIssueDetailContent({
  issueId,
  onDeleted,
  onUpdated,
}: TeamIssueDetailContentProps) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";

  const [issue, setIssue] = React.useState<WorkspaceIssue | null>(null);
  const [presets, setPresets] = React.useState<Preset[]>([]);
  const [projects, setProjects] = React.useState<ProjectItem[]>([]);
  const [form, setForm] = React.useState<IssueDetailFormData>({
    status: "todo",
    priority: "medium",
    relatedProjectId: "none",
    selectedPresetId: "none",
    triggerMode: "persistent_sandbox",
    scheduleCron: "0 * * * *",
    prompt: "",
  });
  const [loadState, setLoadState] = React.useState<IssueDetailLoadState>("loading");
  const [isSaving, setIsSaving] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);

  const formRef = React.useRef(form);
  formRef.current = form;
  const isSavingRef = React.useRef(false);
  const issueRef = React.useRef(issue);
  issueRef.current = issue;
  const onUpdatedRef = React.useRef(onUpdated);
  onUpdatedRef.current = onUpdated;
  const skipNextAutoSaveRef = React.useRef(true);

  const updateForm = React.useCallback((patch: Partial<FormData>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  }, []);

  const loadIssue = React.useCallback(async () => {
    setLoadState("loading");
    try {
      const [nextIssue, nextPresets, nextProjects] = await Promise.all([
        issuesApi.getIssue(issueId),
        presetsService.listPresets(),
        projectsService.listProjects(),
      ]);
      setIssue(nextIssue);
      setPresets(
        nextPresets.filter((item) => item.scope !== "personal" || item.user_id),
      );
      setProjects(nextProjects);
      skipNextAutoSaveRef.current = true;
      setForm(createIssueDetailFormData(nextIssue));
      setLoadState("loaded");
    } catch (error) {
      console.error("[Issues] load detail failed", error);
      setLoadState("error");
      toast.error(t("issues.toasts.loadFailed"));
    }
  }, [issueId, t]);

  React.useEffect(() => {
    void loadIssue();
  }, [loadIssue]);

  const refreshIssue = React.useCallback(async () => {
    try {
      const nextIssue = await issuesApi.getIssue(issueId);
      setIssue(nextIssue);
      skipNextAutoSaveRef.current = true;
      setForm((prev) => ({
        ...prev,
        ...createIssueDetailFormData(nextIssue),
      }));
    } catch {
      toast.error(t("issues.toasts.loadFailed"));
    }
  }, [issueId, t]);

  const autoSave = React.useCallback(async (currentForm: IssueDetailFormData) => {
    const currentIssue = issueRef.current;
    if (!currentIssue || isSavingRef.current) return;
    isSavingRef.current = true;
    setIsSaving(true);
    try {
      const updated = await issuesApi.updateIssue(
        currentIssue.board_id,
        currentIssue.issue_id,
        {
          status: currentForm.status,
          priority: currentForm.priority,
          related_project_id:
            currentForm.relatedProjectId === "none"
              ? null
              : currentForm.relatedProjectId,
          assignee_preset_id:
            currentForm.selectedPresetId === "none"
              ? null
              : Number(currentForm.selectedPresetId),
          trigger_mode:
            currentForm.selectedPresetId === "none"
              ? undefined
              : currentForm.triggerMode,
          schedule_cron:
            currentForm.selectedPresetId === "none" ||
            currentForm.triggerMode !== "scheduled_task"
              ? null
              : currentForm.scheduleCron,
          assignment_prompt:
            currentForm.selectedPresetId === "none"
              ? null
              : currentForm.prompt,
        },
      );
      setIssue(updated);
      issueRef.current = updated;
      onUpdatedRef.current(updated);
    } catch (error) {
      console.error("[Issues] auto-save failed", error);
      toast.error(t("issues.toasts.issueUpdateFailed"));
    } finally {
      isSavingRef.current = false;
      setIsSaving(false);
    }
  }, [t]);

  React.useEffect(() => {
    if (!shouldScheduleIssueDetailAutoSave(loadState, skipNextAutoSaveRef.current)) {
      skipNextAutoSaveRef.current = false;
      return;
    }
    const timer = setTimeout(() => {
      void autoSave(formRef.current);
    }, 600);
    return () => clearTimeout(timer);
  }, [form, loadState, autoSave]);

  const runAction = async (
    action: "trigger" | "retry" | "cancel" | "release",
  ) => {
    try {
      if (action === "trigger") {
        await issuesApi.triggerAssignment(issueId);
      } else if (action === "retry") {
        await issuesApi.retryAssignment(issueId);
      } else if (action === "cancel") {
        await issuesApi.cancelAssignment(issueId);
      } else {
        await issuesApi.releaseAssignment(issueId);
      }
      await refreshIssue();
      toast.success(t(ACTION_TOAST_KEYS[action]));
    } catch (error) {
      console.error(`[Issues] ${action} assignment failed`, error);
      toast.error(t("issues.toasts.actionFailed"));
    }
  };

  const deleteIssue = async () => {
    if (!issue) return;
    setIsDeleting(true);
    try {
      await issuesApi.deleteIssue(issue.board_id, issue.issue_id);
      toast.success(t("issues.toasts.issueDeleted"));
      onDeleted(issue.issue_id);
    } catch (error) {
      console.error("[Issues] delete issue failed", error);
      toast.error(t("issues.toasts.issueDeleteFailed"));
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  const assignment = issue?.agent_assignment;
  const executionMeta = getAssignmentExecutionMeta(assignment);

  return (
    <>
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-border/70 px-5 py-4 sm:px-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-foreground">
                  {issue?.title ?? t("issues.detailTitle")}
                </h2>
                {isSaving ? (
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
                    <span className="relative inline-flex size-2 rounded-full bg-primary" />
                  </span>
                ) : null}
              </div>
              <p className="text-sm text-muted-foreground">
                {t("issues.detailSubtitle", { issueId })}
              </p>
            </div>
            {issue ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDeleteDialogOpen(true)}
              >
                <Trash2 className="size-4" />
                {t("issues.actions.deleteIssue")}
              </Button>
            ) : null}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          {loadState === "loading" ? (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="space-y-6">
                <Card className="border-border/60">
                  <CardHeader>
                    <Skeleton className="h-5 w-28" />
                    <Skeleton className="h-4 w-40" />
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <Skeleton className="h-8 w-48 rounded-xl" />
                    <Skeleton className="h-20 rounded-2xl" />
                    <Skeleton className="h-10 rounded-xl" />
                  </CardContent>
                </Card>
                <Card className="border-border/60">
                  <CardHeader>
                    <Skeleton className="h-5 w-28" />
                    <Skeleton className="h-4 w-56" />
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <Skeleton className="h-10 rounded-xl" />
                    <Skeleton className="h-10 rounded-xl" />
                    <Skeleton className="h-10 w-40 rounded-xl" />
                  </CardContent>
                </Card>
                <Card className="border-border/60">
                  <CardHeader>
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-4 w-40" />
                  </CardHeader>
                  <CardContent className="pb-6">
                    <Skeleton className="h-32 rounded-2xl" />
                  </CardContent>
                </Card>
              </div>
              <div className="space-y-6">
                <Card className="border-border/60">
                  <CardHeader>
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-4 w-32" />
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <Skeleton className="h-32 rounded-2xl" />
                    <Skeleton className="h-10 rounded-xl" />
                    <Skeleton className="h-10 rounded-xl" />
                    <Skeleton className="h-10 rounded-xl" />
                  </CardContent>
                </Card>
                <Card className="border-border/60">
                  <CardHeader>
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-4 w-56" />
                  </CardHeader>
                  <CardContent className="pb-6">
                    <Skeleton className="h-28 rounded-2xl" />
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : loadState === "error" && !issue ? (
            <Card className="border-border/60">
              <CardContent className="p-6">
                <Empty className="min-h-72 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                  <EmptyContent>
                    <EmptyMedia variant="icon">
                      <Ticket className="size-5" />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>{t("issues.states.loadErrorTitle")}</EmptyTitle>
                      <EmptyDescription>
                        {t("issues.states.loadErrorDescription")}
                      </EmptyDescription>
                    </EmptyHeader>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void loadIssue()}
                    >
                      <RefreshCw className="size-4" />
                      {t("issues.actions.retryLoad")}
                    </Button>
                  </EmptyContent>
                </Empty>
              </CardContent>
            </Card>
          ) : issue ? (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="space-y-6">
                <Card className="border-border/60">
                  <CardHeader>
                    <CardTitle>{t("issues.sections.overview")}</CardTitle>
                    <CardDescription>
                      {t("issues.sections.dialogOverviewDescription")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">
                        {formatIssueStatus(t, issue.status)}
                      </Badge>
                      {assignment ? (
                        <AssignmentBadge assignment={assignment} />
                      ) : null}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {issue.description || t("issues.emptyDescription")}
                    </p>
                    <div className="grid gap-4 md:grid-cols-2">
                      <FieldSelect
                        label={t("issues.fields.status")}
                        value={form.status}
                        onValueChange={(v) =>
                          updateForm({ status: v as WorkspaceIssue["status"] })
                        }
                      >
                        <SelectItem value="todo">
                          {t("issues.statuses.todo")}
                        </SelectItem>
                        <SelectItem value="in_progress">
                          {t("issues.statuses.in_progress")}
                        </SelectItem>
                        <SelectItem value="done">
                          {t("issues.statuses.done")}
                        </SelectItem>
                        <SelectItem value="canceled">
                          {t("issues.statuses.canceled")}
                        </SelectItem>
                      </FieldSelect>
                      <FieldSelect
                        label={t("issues.fields.priority")}
                        value={form.priority}
                        onValueChange={(v) =>
                          updateForm({
                            priority: v as WorkspaceIssue["priority"],
                          })
                        }
                      >
                        <SelectItem value="urgent">
                          {t("issues.priorities.urgent")}
                        </SelectItem>
                        <SelectItem value="medium">
                          {t("issues.priorities.medium")}
                        </SelectItem>
                        <SelectItem value="high">
                          {t("issues.priorities.high")}
                        </SelectItem>
                        <SelectItem value="low">
                          {t("issues.priorities.low")}
                        </SelectItem>
                      </FieldSelect>
                    </div>
                    <FieldSelect
                      label={t("issues.fields.project")}
                      value={form.relatedProjectId}
                      onValueChange={(v) => updateForm({ relatedProjectId: v })}
                      placeholder={t("issues.placeholders.project")}
                    >
                      <SelectItem value="none">{t("issues.none")}</SelectItem>
                      {projects.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          {project.name}
                        </SelectItem>
                      ))}
                    </FieldSelect>
                  </CardContent>
                </Card>

                <Card className="border-border/60">
                  <CardHeader>
                    <CardTitle>{t("issues.sections.assignment")}</CardTitle>
                    <CardDescription>
                      {t("issues.sections.assignmentDescription")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <div className="grid gap-4 md:grid-cols-2">
                      <FieldSelect
                        label={t("issues.fields.agentPreset")}
                        value={form.selectedPresetId}
                        onValueChange={(v) =>
                          updateForm({ selectedPresetId: v })
                        }
                        placeholder={t("issues.placeholders.preset")}
                      >
                        <SelectItem value="none">{t("issues.none")}</SelectItem>
                        {presets.map((preset) => (
                          <SelectItem
                            key={preset.preset_id}
                            value={String(preset.preset_id)}
                          >
                            {preset.name}
                          </SelectItem>
                        ))}
                      </FieldSelect>
                      <FieldSelect
                        label={t("issues.fields.triggerMode")}
                        value={form.triggerMode}
                        onValueChange={(v) =>
                          updateForm({
                            triggerMode: v as IssueDetailFormData["triggerMode"],
                          })
                        }
                      >
                        <SelectItem value="persistent_sandbox">
                          {t("issues.triggerModes.persistent_sandbox")}
                        </SelectItem>
                        <SelectItem value="scheduled_task">
                          {t("issues.triggerModes.scheduled_task")}
                        </SelectItem>
                      </FieldSelect>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        {t("issues.fields.schedule")}
                      </p>
                      <Input
                        value={form.scheduleCron}
                        onChange={(e) =>
                          updateForm({ scheduleCron: e.target.value })
                        }
                        disabled={form.triggerMode !== "scheduled_task"}
                        placeholder="0 * * * *"
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border/60">
                  <CardHeader>
                    <CardTitle>{t("issues.sections.prompt")}</CardTitle>
                    <CardDescription>
                      {t("issues.sections.promptDescription")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 pb-6">
                    <Textarea
                      value={form.prompt}
                      onChange={(e) => updateForm({ prompt: e.target.value })}
                      rows={10}
                      placeholder={t("issues.placeholders.prompt")}
                    />
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card className="border-border/60">
                  <CardHeader>
                    <CardTitle>{t("issues.executionTitle")}</CardTitle>
                    <CardDescription>
                      {t("issues.sections.executionDescription")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 pb-6">
                    <div className="space-y-3 rounded-2xl border border-border/60 p-4">
                      <InfoRow
                        label={t("issues.fields.assignmentStatus")}
                        value={
                          assignment
                            ? formatAssignmentStatus(t, assignment.status)
                            : t("issues.unassigned")
                        }
                      />
                      <InfoRow
                        label={t("issues.fields.session")}
                        value={assignment?.session_id ?? ""}
                        mono
                      />
                      <InfoRow
                        label={t("issues.fields.container")}
                        value={assignment?.container_id ?? ""}
                        mono
                      />
                      <InfoRow
                        label={t("issues.fields.lastTriggeredAt")}
                        value={
                          executionMeta.lastTriggeredAt
                            ? formatDateTime(executionMeta.lastTriggeredAt)
                            : ""
                        }
                      />
                      <InfoRow
                        label={t("issues.fields.lastCompletedAt")}
                        value={
                          executionMeta.lastCompletedAt
                            ? formatDateTime(executionMeta.lastCompletedAt)
                            : ""
                        }
                      />
                    </div>
                    <div className="grid gap-2">
                      <Button
                        type="button"
                        onClick={() => void runAction("trigger")}
                      >
                        {t("issues.actions.trigger")}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => void runAction("retry")}
                      >
                        {t("issues.actions.retry")}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => void runAction("cancel")}
                      >
                        {t("issues.actions.cancel")}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => void runAction("release")}
                      >
                        {t("issues.actions.release")}
                      </Button>
                      {assignment?.session_id ? (
                        <Button type="button" variant="secondary" asChild>
                          <Link href={`/${lng}/chat/${assignment.session_id}`}>
                            {t("issues.actions.openSession")}
                          </Link>
                        </Button>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("issues.dialogs.deleteIssueTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("issues.dialogs.deleteIssueDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => void deleteIssue()}>
              {isDeleting
                ? t("issues.actions.deletingIssue")
                : t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
