"use client";

import * as React from "react";
import Link from "next/link";
import {
  CheckCheck,
  ChevronDown,
  Copy,
  CircleDashed,
  ExternalLink,
  Flag,
  FolderOpen,
  LoaderCircle,
  MoreHorizontal,
  RefreshCw,
  Slash,
  Sparkles,
  Ticket,
  TimerReset,
  Trash2,
} from "lucide-react";
import { useRouter } from "next/navigation";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { Textarea } from "@/components/ui/textarea";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { issuesApi } from "@/features/issues/api/issues-api";
import { getAssignmentExecutionMeta } from "@/features/issues/lib/issue-detail-view";
import {
  createIssueDetailFormData,
  getIssueDetailPrioritySelectValue,
  shouldScheduleIssueDetailAutoSave,
  type IssueDetailFormData,
  type IssueDetailLoadState,
} from "@/features/issues/lib/issue-detail-form";
import {
  formatAssignmentStatus,
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

function DetailFieldHeader({
  icon,
  label,
}: {
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
      {icon}
      <span>{label}</span>
    </div>
  );
}

function renderStatusOption(
  t: ReturnType<typeof useT>["t"],
  status: WorkspaceIssue["status"],
) {
  const iconClassName = "size-3.5";

  if (status === "in_progress") {
    return (
      <>
        <LoaderCircle className={`${iconClassName} text-primary`} />
        <span>{t("issues.statuses.in_progress")}</span>
      </>
    );
  }
  if (status === "done") {
    return (
      <>
        <CheckCheck className={`${iconClassName} text-primary`} />
        <span>{t("issues.statuses.done")}</span>
      </>
    );
  }
  if (status === "canceled") {
    return (
      <>
        <Slash className={`${iconClassName} text-muted-foreground`} />
        <span>{t("issues.statuses.canceled")}</span>
      </>
    );
  }
  return (
    <>
      <CircleDashed className={`${iconClassName} text-muted-foreground`} />
      <span>{t("issues.statuses.todo")}</span>
    </>
  );
}

function renderPriorityOption(
  t: ReturnType<typeof useT>["t"],
  priority: "high" | "medium" | "low",
) {
  const toneClassName =
    priority === "high"
      ? "text-red-500"
      : priority === "low"
        ? "text-muted-foreground"
        : "text-amber-500";

  return (
    <>
      <Flag className={`size-3.5 ${toneClassName}`} />
      <span>{t(`issues.priorities.${priority}`)}</span>
    </>
  );
}

function renderStatusIcon(status: WorkspaceIssue["status"]) {
  const iconClassName = "size-3.5";

  if (status === "in_progress") {
    return <LoaderCircle className={`${iconClassName} text-primary`} />;
  }
  if (status === "done") {
    return <CheckCheck className={`${iconClassName} text-primary`} />;
  }
  if (status === "canceled") {
    return <Slash className={`${iconClassName} text-muted-foreground`} />;
  }
  return <CircleDashed className={`${iconClassName} text-muted-foreground`} />;
}

function renderPriorityIcon(priority: "high" | "medium" | "low") {
  const toneClassName =
    priority === "high"
      ? "text-red-500"
      : priority === "low"
        ? "text-muted-foreground"
        : "text-amber-500";

  return <Flag className={`size-3.5 ${toneClassName}`} />;
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
  const router = useRouter();

  const [issue, setIssue] = React.useState<WorkspaceIssue | null>(null);
  const [boardName, setBoardName] = React.useState<string | null>(null);
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

  const updateForm = React.useCallback((patch: Partial<IssueDetailFormData>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  }, []);

  const loadIssue = React.useCallback(async () => {
    setLoadState("loading");
    try {
      const nextIssue = await issuesApi.getIssue(issueId);
      const [nextPresets, nextProjects, nextBoards] = await Promise.all([
        presetsService.listPresets(),
        projectsService.listProjects(),
        issuesApi.listBoards(nextIssue.workspace_id),
      ]);
      setIssue(nextIssue);
      setBoardName(
        nextBoards.find((board) => board.board_id === nextIssue.board_id)?.name ?? null,
      );
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
      const nextBoards = await issuesApi.listBoards(nextIssue.workspace_id);
      setIssue(nextIssue);
      setBoardName(
        nextBoards.find((board) => board.board_id === nextIssue.board_id)?.name ?? null,
      );
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
  const selectedPreset =
    form.selectedPresetId !== "none"
      ? presets.find((preset) => String(preset.preset_id) === form.selectedPresetId) ?? null
      : null;
  const relatedProject =
    form.relatedProjectId !== "none"
      ? projects.find((project) => project.id === form.relatedProjectId) ?? null
      : null;
  const collaboratorLabel =
    selectedPreset?.name ??
    issue?.assignee_user_id ??
    t("issues.unassigned");
  const collaboratorFallback = collaboratorLabel.charAt(0).toUpperCase() || "?";

  const copyText = React.useCallback(
    async (value: string) => {
      try {
        await navigator.clipboard.writeText(value);
        toast.success(t("common.copy"));
      } catch {
        toast.error(t("issues.toasts.actionFailed"));
      }
    },
    [t],
  );

  return (
    <>
      <div className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-border/60 px-7 py-6">
          <div className="flex items-start justify-between gap-4 pr-14">
            <div className="flex items-center gap-2">
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">
                {issue?.title ?? t("issues.detailTitle")}
              </h2>
              {isSaving ? (
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary/60" />
                  <span className="relative inline-flex size-2 rounded-full bg-primary" />
                </span>
              ) : null}
            </div>
            <div className="flex items-center gap-3">
              <div className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/80 px-3 py-1.5 text-sm text-muted-foreground">
                <span className="size-2 rounded-full bg-primary/70" />
                <span>
                  {t("issues.context.boardPill", {
                    name: boardName ?? t("issues.boardsTitle"),
                  })}
                </span>
              </div>
              {issue ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="size-10 rounded-xl"
                      aria-label={t("header.more")}
                    >
                      <MoreHorizontal className="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48 rounded-xl p-2">
                    <DropdownMenuItem onSelect={() => void copyText(issue.issue_id)}>
                      <Copy className="size-4" />
                      {t("issues.actions.copyIssueId")}
                    </DropdownMenuItem>
                    {relatedProject ? (
                      <DropdownMenuItem
                        onSelect={() => router.push(`/${lng}/projects/${relatedProject.id}`)}
                      >
                        <FolderOpen className="size-4" />
                        {t("issues.actions.viewRelatedProject")}
                      </DropdownMenuItem>
                    ) : null}
                    <DropdownMenuItem onSelect={() => void copyText(window.location.href)}>
                      <ExternalLink className="size-4" />
                      {t("issues.actions.copyShareLink")}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      variant="destructive"
                      onSelect={() => setDeleteDialogOpen(true)}
                    >
                      <Trash2 className="size-4" />
                      {t("issues.actions.deleteIssue")}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-7 py-6">
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
            <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="space-y-8">
                <section className="space-y-6 border-b border-border/60 pb-7">
                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold tracking-tight text-foreground">
                      {t("issues.sections.collaboration")}
                    </h3>
                    <div className="grid gap-5 md:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)_minmax(0,0.75fr)]">
                      <div className="flex items-center gap-4">
                        {selectedPreset ? (
                          <div className="flex size-14 items-center justify-center rounded-2xl bg-muted/20">
                            <PresetGlyph preset={selectedPreset} variant="picker" />
                          </div>
                        ) : (
                          <Avatar className="size-14 border border-border/60 bg-muted/50">
                            <AvatarFallback className="bg-muted text-base font-semibold text-foreground">
                              {collaboratorFallback}
                            </AvatarFallback>
                          </Avatar>
                        )}
                        <div className="space-y-1.5">
                          <p className="text-lg font-medium text-foreground">
                            {collaboratorLabel}
                          </p>
                          <div className="flex flex-wrap items-center gap-2">
                            {selectedPreset ? (
                              <Badge variant="secondary">
                                {t("issues.fields.agentPreset")}
                              </Badge>
                            ) : (
                              <Badge variant="outline">{t("issues.unassigned")}</Badge>
                            )}
                            {assignment ? <AssignmentBadge assignment={assignment} /> : null}
                          </div>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                          {t("issues.fields.createdAt")}
                        </p>
                        <p className="text-sm font-medium text-foreground">
                          {formatDateTime(issue.created_at)}
                        </p>
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                          {t("issues.fields.updatedAt")}
                        </p>
                        <p className="text-sm font-medium text-foreground">
                          {formatDateTime(issue.updated_at)}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-auto rounded-2xl border border-border/50 bg-background/80 px-4 py-3 hover:bg-accent/20"
                        >
                          <div className="flex w-full flex-col gap-4 text-left">
                            <DetailFieldHeader
                              icon={renderStatusIcon(form.status)}
                              label={t("issues.fields.status")}
                            />
                            <div className="flex w-full items-center justify-end gap-2 text-sm font-medium text-foreground">
                              <span>{t(`issues.statuses.${form.status}`)}</span>
                              <ChevronDown className="size-4 text-muted-foreground" />
                            </div>
                          </div>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="z-[80] min-w-40">
                        <DropdownMenuItem
                          onSelect={() => updateForm({ status: "todo" })}
                        >
                          {renderStatusOption(t, "todo")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ status: "in_progress" })}
                        >
                          {renderStatusOption(t, "in_progress")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ status: "done" })}
                        >
                          {renderStatusOption(t, "done")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ status: "canceled" })}
                        >
                          {renderStatusOption(t, "canceled")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-auto rounded-2xl border border-border/50 bg-background/80 px-4 py-3 hover:bg-accent/20"
                        >
                          <div className="flex w-full flex-col gap-4 text-left">
                            <DetailFieldHeader
                              icon={renderPriorityIcon(
                                getIssueDetailPrioritySelectValue(form.priority),
                              )}
                              label={t("issues.fields.priority")}
                            />
                            <div className="flex w-full items-center justify-end gap-2 text-sm font-medium text-foreground">
                              <span>
                                {t(
                                  `issues.priorities.${getIssueDetailPrioritySelectValue(
                                    form.priority,
                                  )}`,
                                )}
                              </span>
                              <ChevronDown className="size-4 text-muted-foreground" />
                            </div>
                          </div>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="z-[80] min-w-40">
                        <DropdownMenuItem
                          onSelect={() => updateForm({ priority: "high" })}
                        >
                          {renderPriorityOption(t, "high")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ priority: "medium" })}
                        >
                          {renderPriorityOption(t, "medium")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ priority: "low" })}
                        >
                          {renderPriorityOption(t, "low")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-auto rounded-2xl border border-border/50 bg-background/80 px-4 py-3 hover:bg-accent/20"
                        >
                          <div className="flex w-full flex-col gap-4 text-left">
                            <DetailFieldHeader
                              icon={<FolderOpen className="size-3.5" />}
                              label={t("issues.fields.project")}
                            />
                            <div className="flex w-full items-center justify-end gap-2 text-sm font-medium text-foreground">
                              <span>{relatedProject?.name ?? t("issues.none")}</span>
                              <ChevronDown className="size-4 text-muted-foreground" />
                            </div>
                          </div>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="z-[80] min-w-40">
                        <DropdownMenuItem onSelect={() => updateForm({ relatedProjectId: "none" })}>
                          {t("issues.none")}
                        </DropdownMenuItem>
                        {projects.map((project) => (
                          <DropdownMenuItem
                            key={project.id}
                            onSelect={() => updateForm({ relatedProjectId: project.id })}
                          >
                            {project.name}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-auto rounded-2xl border border-border/50 bg-background/80 px-4 py-3 hover:bg-accent/20"
                        >
                          <div className="flex w-full flex-col gap-4 text-left">
                            <DetailFieldHeader
                              icon={<Sparkles className="size-3.5" />}
                              label={t("issues.fields.agentPreset")}
                            />
                            <div className="flex w-full items-center justify-end gap-2 text-sm font-medium text-foreground">
                              <span>{selectedPreset?.name ?? t("issues.none")}</span>
                              <ChevronDown className="size-4 text-muted-foreground" />
                            </div>
                          </div>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="z-[80] min-w-40">
                        <DropdownMenuItem onSelect={() => updateForm({ selectedPresetId: "none" })}>
                          {t("issues.none")}
                        </DropdownMenuItem>
                        {presets.map((preset) => (
                          <DropdownMenuItem
                            key={preset.preset_id}
                            onSelect={() => updateForm({ selectedPresetId: String(preset.preset_id) })}
                          >
                            {preset.name}
                          </DropdownMenuItem>
                        ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          className="h-auto rounded-2xl border border-border/50 bg-background/80 px-4 py-3 hover:bg-accent/20"
                        >
                          <div className="flex w-full flex-col gap-4 text-left">
                            <DetailFieldHeader
                              icon={<TimerReset className="size-3.5" />}
                              label={t("issues.fields.triggerMode")}
                            />
                            <div className="flex w-full items-center justify-end gap-2 text-sm font-medium text-foreground">
                              <span>{t(`issues.triggerModes.${form.triggerMode}`)}</span>
                              <ChevronDown className="size-4 text-muted-foreground" />
                            </div>
                          </div>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="z-[80] min-w-40">
                        <DropdownMenuItem
                          onSelect={() => updateForm({ triggerMode: "persistent_sandbox" })}
                        >
                          {t("issues.triggerModes.persistent_sandbox")}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onSelect={() => updateForm({ triggerMode: "scheduled_task" })}
                        >
                          {t("issues.triggerModes.scheduled_task")}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </section>

                <section className="space-y-4 border-b border-border/60 pb-7">
                  <div className="space-y-1">
                    <h3 className="text-xl font-semibold tracking-tight text-foreground">
                      {t("issues.sections.triggerSetup")}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {t("issues.sections.triggerSetupDescription")}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                      {t("issues.fields.schedule")}
                    </p>
                    <Input
                      value={form.scheduleCron}
                      onChange={(e) => updateForm({ scheduleCron: e.target.value })}
                      disabled={form.triggerMode !== "scheduled_task"}
                      placeholder="0 * * * *"
                      className="h-11 rounded-2xl border-border/50 bg-background/80 shadow-none"
                    />
                  </div>
                  <div className="space-y-2">
                    <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                      {t("issues.fields.prompt")}
                    </p>
                    <Textarea
                      value={form.prompt}
                      onChange={(e) => updateForm({ prompt: e.target.value })}
                      rows={6}
                      placeholder={t("issues.placeholders.prompt")}
                      className="min-h-36 rounded-2xl border-border/50 bg-background/80 shadow-none"
                    />
                  </div>
                </section>
              </div>

              <aside className="space-y-6 border-t border-border/60 pt-6 lg:border-t-0 lg:border-l lg:pl-6 lg:pt-0">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold tracking-tight text-foreground">
                    执行状态
                  </h3>
                  <p className="max-w-xs text-sm leading-7 text-muted-foreground">
                    不离开当前 board，就地执行 assignment 相关动作。
                  </p>
                </div>
                <div className="space-y-3 text-sm">
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted-foreground">{t("issues.fields.assignmentStatus")}</span>
                    <span className="text-right font-medium text-foreground">
                      {assignment
                        ? formatAssignmentStatus(t, assignment.status)
                        : t("issues.unassigned")}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted-foreground">{t("issues.fields.session")}</span>
                    <span className="max-w-[12rem] break-all text-right font-medium text-foreground">
                      {assignment?.session_id ?? t("issues.none")}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted-foreground">{t("issues.fields.container")}</span>
                    <span className="max-w-[12rem] break-all text-right font-medium text-foreground">
                      {assignment?.container_id ?? t("issues.none")}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted-foreground">{t("issues.fields.lastTriggeredAt")}</span>
                    <span className="text-right font-medium text-foreground">
                      {executionMeta.lastTriggeredAt
                        ? formatDateTime(executionMeta.lastTriggeredAt)
                        : t("issues.none")}
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-muted-foreground">{t("issues.fields.lastCompletedAt")}</span>
                    <span className="text-right font-medium text-foreground">
                      {executionMeta.lastCompletedAt
                        ? formatDateTime(executionMeta.lastCompletedAt)
                        : t("issues.none")}
                    </span>
                  </div>
                </div>
                <div className="grid gap-3">
                  <Button type="button" className="h-11 rounded-xl" onClick={() => void runAction("trigger")}>
                    {t("issues.actions.trigger")}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 rounded-xl"
                    onClick={() => void runAction("retry")}
                  >
                    {t("issues.actions.retry")}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 rounded-xl"
                    onClick={() => void runAction("cancel")}
                  >
                    {t("issues.actions.cancel")}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="h-11 rounded-xl"
                    onClick={() => void runAction("release")}
                  >
                    {t("issues.actions.release")}
                  </Button>
                  {assignment?.session_id ? (
                    <Button
                      type="button"
                      variant="secondary"
                      className="h-11 rounded-xl"
                      asChild
                    >
                      <Link href={`/${lng}/chat/${assignment.session_id}`}>
                        {t("issues.actions.openSession")}
                      </Link>
                    </Button>
                  ) : null}
                </div>
              </aside>
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
