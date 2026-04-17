"use client";

import * as React from "react";
import Link from "next/link";
import { Bot, RefreshCw, Ticket, Trash2 } from "lucide-react";
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
  formatAssignmentStatus,
  formatIssuePriority,
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

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

interface TeamIssueDetailContentProps {
  issueId: string;
  onDeleted: (issueId: string) => void;
}

export function TeamIssueDetailContent({
  issueId,
  onDeleted,
}: TeamIssueDetailContentProps) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";
  const [issue, setIssue] = React.useState<WorkspaceIssue | null>(null);
  const [presets, setPresets] = React.useState<Preset[]>([]);
  const [projects, setProjects] = React.useState<ProjectItem[]>([]);
  const [selectedPresetId, setSelectedPresetId] = React.useState<string>("none");
  const [triggerMode, setTriggerMode] = React.useState<
    "persistent_sandbox" | "scheduled_task"
  >("persistent_sandbox");
  const [scheduleCron, setScheduleCron] = React.useState("0 * * * *");
  const [prompt, setPrompt] = React.useState("");
  const [relatedProjectId, setRelatedProjectId] = React.useState<string>("none");
  const [isLoading, setIsLoading] = React.useState(true);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);

  const load = React.useCallback(async () => {
    setIsLoading(true);
    setLoadFailed(false);
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
      setSelectedPresetId(
        nextIssue.assignee_preset_id ? String(nextIssue.assignee_preset_id) : "none",
      );
      setTriggerMode(nextIssue.agent_assignment?.trigger_mode ?? "persistent_sandbox");
      setScheduleCron(nextIssue.agent_assignment?.schedule_cron ?? "0 * * * *");
      setPrompt(nextIssue.agent_assignment?.prompt ?? nextIssue.description ?? "");
      setRelatedProjectId(nextIssue.related_project_id ?? "none");
    } catch (error) {
      console.error("[Issues] load detail failed", error);
      setLoadFailed(true);
      toast.error(t("issues.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [issueId, t]);

  React.useEffect(() => {
    void load();
  }, [load]);

  const saveAssignment = async () => {
    if (!issue) {
      return;
    }
    setIsSaving(true);
    try {
      const updated = await issuesApi.updateIssue(issue.board_id, issue.issue_id, {
        assignee_preset_id:
          selectedPresetId === "none" ? null : Number(selectedPresetId),
        trigger_mode: selectedPresetId === "none" ? undefined : triggerMode,
        schedule_cron:
          selectedPresetId === "none" || triggerMode !== "scheduled_task"
            ? null
            : scheduleCron,
        assignment_prompt: selectedPresetId === "none" ? null : prompt,
        related_project_id: relatedProjectId === "none" ? null : relatedProjectId,
      });
      setIssue(updated);
      toast.success(t("issues.toasts.assignmentSaved"));
    } catch (error) {
      console.error("[Issues] save assignment failed", error);
      toast.error(t("issues.toasts.assignmentSaveFailed"));
    } finally {
      setIsSaving(false);
    }
  };

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
      await load();
      toast.success(
        t(
          action === "trigger"
            ? "issues.toasts.triggered"
            : action === "retry"
              ? "issues.toasts.retried"
              : action === "cancel"
                ? "issues.toasts.cancelled"
                : "issues.toasts.released",
        ),
      );
    } catch (error) {
      console.error(`[Issues] ${action} assignment failed`, error);
      toast.error(t("issues.toasts.actionFailed"));
    }
  };

  const deleteIssue = async () => {
    if (!issue) {
      return;
    }
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
              <h2 className="text-xl font-semibold text-foreground">
                {issue?.title ?? t("issues.detailTitle")}
              </h2>
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
          {isLoading ? (
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
          ) : loadFailed && !issue ? (
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
                    <Button type="button" variant="outline" onClick={() => void load()}>
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
                      <Badge variant="outline">
                        {formatIssuePriority(t, issue.priority)}
                      </Badge>
                      {assignment ? <AssignmentBadge assignment={assignment} /> : null}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {issue.description || t("issues.emptyDescription")}
                    </p>
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        {t("issues.fields.project")}
                      </p>
                      <Select
                        value={relatedProjectId}
                        onValueChange={setRelatedProjectId}
                      >
                        <SelectTrigger>
                          <SelectValue
                            placeholder={t("issues.placeholders.project")}
                          />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">{t("issues.none")}</SelectItem>
                          {projects.map((project) => (
                            <SelectItem key={project.id} value={project.id}>
                              {project.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
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
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">
                          {t("issues.fields.agentPreset")}
                        </p>
                        <Select
                          value={selectedPresetId}
                          onValueChange={setSelectedPresetId}
                        >
                          <SelectTrigger>
                            <SelectValue
                              placeholder={t("issues.placeholders.preset")}
                            />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">{t("issues.none")}</SelectItem>
                            {presets.map((preset) => (
                              <SelectItem
                                key={preset.preset_id}
                                value={String(preset.preset_id)}
                              >
                                {preset.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">
                          {t("issues.fields.triggerMode")}
                        </p>
                        <Select
                          value={triggerMode}
                          onValueChange={(value) =>
                            setTriggerMode(value as typeof triggerMode)
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="persistent_sandbox">
                              {t("issues.triggerModes.persistent_sandbox")}
                            </SelectItem>
                            <SelectItem value="scheduled_task">
                              {t("issues.triggerModes.scheduled_task")}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">
                        {t("issues.fields.schedule")}
                      </p>
                      <Input
                        value={scheduleCron}
                        onChange={(event) => setScheduleCron(event.target.value)}
                        disabled={triggerMode !== "scheduled_task"}
                        placeholder="0 * * * *"
                      />
                    </div>

                    <Button
                      type="button"
                      onClick={() => void saveAssignment()}
                      disabled={isSaving}
                    >
                      <Bot className="size-4" />
                      {t("issues.actions.saveAssignment")}
                    </Button>
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
                      value={prompt}
                      onChange={(event) => setPrompt(event.target.value)}
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
                    <div className="rounded-2xl border border-border/60 p-4">
                      <p className="text-sm font-medium">
                        {t("issues.fields.assignmentStatus")}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {assignment
                          ? formatAssignmentStatus(t, assignment.status)
                          : t("issues.unassigned")}
                      </p>
                      <p className="mt-3 text-sm font-medium">
                        {t("issues.fields.session")}
                      </p>
                      <p className="mt-1 break-all text-sm text-muted-foreground">
                        {assignment?.session_id ?? t("issues.none")}
                      </p>
                      <p className="mt-3 text-sm font-medium">
                        {t("issues.fields.container")}
                      </p>
                      <p className="mt-1 break-all text-sm text-muted-foreground">
                        {assignment?.container_id ?? t("issues.none")}
                      </p>
                      <p className="mt-3 text-sm font-medium">
                        {t("issues.fields.lastTriggeredAt")}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {executionMeta.lastTriggeredAt
                          ? formatDateTime(executionMeta.lastTriggeredAt)
                          : t("issues.none")}
                      </p>
                      <p className="mt-3 text-sm font-medium">
                        {t("issues.fields.lastCompletedAt")}
                      </p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {executionMeta.lastCompletedAt
                          ? formatDateTime(executionMeta.lastCompletedAt)
                          : t("issues.none")}
                      </p>
                    </div>
                    <div className="grid gap-2">
                      <Button type="button" onClick={() => void runAction("trigger")}>
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

                <Card className="border-border/60">
                  <CardHeader>
                    <CardTitle>{t("issues.sections.executionPreview")}</CardTitle>
                    <CardDescription>
                      {t("issues.sections.executionPreviewDescription")}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 pb-6">
                    <div className="rounded-2xl border border-dashed border-border/70 bg-muted/10 p-4 text-sm text-muted-foreground">
                      <p>
                        {t("issues.preview.executionMode")}:{" "}
                        {t(`issues.triggerModes.${triggerMode}`)}
                      </p>
                      <p className="mt-2">
                        {executionMeta.isScheduled
                          ? `${t("issues.fields.schedule")}: ${
                              scheduleCron || t("issues.none")
                            }`
                          : `${t("issues.fields.container")}: ${
                              executionMeta.hasRetainedContainer
                                ? assignment?.container_id
                                : t("issues.none")
                            }`}
                      </p>
                      <p className="mt-2">
                        {executionMeta.hasSession
                          ? `${t("issues.fields.session")}: ${assignment?.session_id}`
                          : t("issues.preview.pendingImpact")}
                      </p>
                      <p className="mt-3 text-xs text-muted-foreground">
                        {t("issues.preview.releaseHint")}
                      </p>
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
            <AlertDialogTitle>{t("issues.dialogs.deleteIssueTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("issues.dialogs.deleteIssueDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => void deleteIssue()}>
              {isDeleting ? t("issues.actions.deletingIssue") : t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
