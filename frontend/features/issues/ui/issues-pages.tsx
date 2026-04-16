"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Bot, ChevronLeft, KanbanSquare, Plus, RefreshCw, Ticket } from "lucide-react";
import { toast } from "sonner";

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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { issuesApi } from "@/features/issues/api/issues-api";
import {
  filterIssuesByQuery,
  summarizeBoardIssues,
} from "@/features/issues/lib/issues-index-view";
import { getAssignmentExecutionMeta } from "@/features/issues/lib/issue-detail-view";
import {
  formatAssignmentStatus,
  formatIssuePriority,
  formatIssueStatus,
} from "@/features/issues/lib/issue-presentation";
import type {
  AgentAssignment,
  WorkspaceBoard,
  WorkspaceIssue,
} from "@/features/issues/model/types";
import { projectsService } from "@/features/projects/api/projects-api";
import type { ProjectItem } from "@/features/projects/types";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useWorkspaceContext } from "@/features/workspaces";
import { TeamContentShell } from "@/features/workspaces/ui/team-content-shell";

function AssignmentBadge({
  assignment,
}: {
  assignment?: AgentAssignment | null;
}) {
  const { t } = useT("translation");
  if (!assignment) return null;
  return (
    <Badge variant="secondary">
      {formatAssignmentStatus(t, assignment.status)}
    </Badge>
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

interface CreateBoardDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (name: string) => Promise<void>;
}

function CreateBoardDialog({
  open,
  onOpenChange,
  onCreate,
}: CreateBoardDialogProps) {
  const { t } = useT("translation");
  const [name, setName] = React.useState("");
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setName("");
      setIsSaving(false);
    }
  }, [open]);

  const handleCreate = async () => {
    setIsSaving(true);
    await onCreate(name);
    setIsSaving(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("issues.dialogs.createBoardTitle")}</DialogTitle>
          <DialogDescription>{t("issues.boardsTitle")}</DialogDescription>
        </DialogHeader>
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t("issues.boardNamePlaceholder")}
          autoFocus
        />
        <DialogFooter>
          <Button
            type="button"
            onClick={() => void handleCreate()}
            disabled={isSaving || !name.trim()}
          >
            {t("issues.actions.createBoard")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface CreateIssueDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  boardName: string | null;
  onCreate: (title: string) => Promise<void>;
}

function CreateIssueDialog({
  open,
  onOpenChange,
  boardName,
  onCreate,
}: CreateIssueDialogProps) {
  const { t } = useT("translation");
  const [title, setTitle] = React.useState("");
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setTitle("");
      setIsSaving(false);
    }
  }, [open]);

  const handleCreate = async () => {
    setIsSaving(true);
    await onCreate(title);
    setIsSaving(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("issues.dialogs.createIssueTitle")}</DialogTitle>
          <DialogDescription>
            {boardName ?? t("issues.emptyBoards")}
          </DialogDescription>
        </DialogHeader>
        <Input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("issues.issueTitlePlaceholder")}
          autoFocus
        />
        <DialogFooter>
          <Button
            type="button"
            onClick={() => void handleCreate()}
            disabled={isSaving || !title.trim()}
          >
            {t("issues.actions.createIssue")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TeamIssuesPageClient() {
  const { t } = useT("translation");
  const lng = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { currentWorkspace } = useWorkspaceContext();
  const [boards, setBoards] = React.useState<WorkspaceBoard[]>([]);
  const [issues, setIssues] = React.useState<WorkspaceIssue[]>([]);
  const [selectedBoardId, setSelectedBoardId] = React.useState<string | null>(null);
  const [boardDialogOpen, setBoardDialogOpen] = React.useState(false);
  const [issueDialogOpen, setIssueDialogOpen] = React.useState(false);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [hasLoadedBoards, setHasLoadedBoards] = React.useState(false);
  const [boardLoadFailed, setBoardLoadFailed] = React.useState(false);
  const [issuesLoadFailed, setIssuesLoadFailed] = React.useState(false);
  const [query, setQuery] = React.useState("");

  const queryIssueId = searchParams.get("issue");
  const [selectedIssueId, setSelectedIssueId] = React.useState<string | null>(queryIssueId);

  React.useEffect(() => {
    setSelectedIssueId(queryIssueId);
  }, [queryIssueId]);

  const selectIssue = React.useCallback(
    (issueId: string) => {
      setSelectedIssueId(issueId);
      const params = new URLSearchParams(searchParams.toString());
      params.set("issue", issueId);
      router.replace(`/${lng}/team/issues?${params.toString()}`, { scroll: false });
    },
    [lng, router, searchParams],
  );

  const clearIssue = React.useCallback(() => {
    setSelectedIssueId(null);
    const params = new URLSearchParams(searchParams.toString());
    params.delete("issue");
    const qs = params.toString();
    router.replace(`/${lng}/team/issues${qs ? `?${qs}` : ""}`, { scroll: false });
  }, [lng, router, searchParams]);

  const loadBoards = React.useCallback(async () => {
    if (!currentWorkspace) return;
    const nextBoards = await issuesApi.listBoards(currentWorkspace.id);
    setBoards(nextBoards);
    setSelectedBoardId((prev) => prev ?? nextBoards[0]?.board_id ?? null);
  }, [currentWorkspace]);

  const loadIssues = React.useCallback(async () => {
    if (!selectedBoardId) {
      setIssues([]);
      return;
    }
    setIssues(await issuesApi.listIssues(selectedBoardId));
  }, [selectedBoardId]);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) return;
    setIsRefreshing(true);
    setBoardLoadFailed(false);
    try {
      await loadBoards();
      setHasLoadedBoards(true);
    } catch (error) {
      console.error("[Issues] refresh failed", error);
      setBoardLoadFailed(true);
      toast.error(t("issues.toasts.loadFailed"));
    } finally {
      setIsRefreshing(false);
    }
  }, [currentWorkspace, loadBoards, t]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  React.useEffect(() => {
    const load = async () => {
      setIssuesLoadFailed(false);
      try {
        await loadIssues();
      } catch (error) {
        console.error("[Issues] load issues failed", error);
        setIssuesLoadFailed(true);
        toast.error(t("issues.toasts.loadFailed"));
      }
    };
    void load();
  }, [loadIssues, t]);

  const selectedBoard = React.useMemo(
    () => boards.find((board) => board.board_id === selectedBoardId) ?? null,
    [boards, selectedBoardId],
  );
  const filteredIssues = React.useMemo(
    () => filterIssuesByQuery(issues, query),
    [issues, query],
  );
  const boardSummary = React.useMemo(
    () => summarizeBoardIssues(issues),
    [issues],
  );

  const createBoard = async (name: string) => {
    if (!currentWorkspace || !name.trim()) return;
    try {
      const created = await issuesApi.createBoard(currentWorkspace.id, {
        name: name.trim(),
      });
      setBoards((prev) => [created, ...prev]);
      setSelectedBoardId(created.board_id);
      setBoardDialogOpen(false);
      toast.success(t("issues.toasts.boardCreated"));
    } catch (error) {
      console.error("[Issues] create board failed", error);
      toast.error(t("issues.toasts.boardCreateFailed"));
    }
  };

  const createIssue = async (title: string) => {
    if (!selectedBoardId || !title.trim()) return;
    try {
      const created = await issuesApi.createIssue(selectedBoardId, {
        title: title.trim(),
      });
      setIssues((prev) => [created, ...prev]);
      setIssueDialogOpen(false);
      toast.success(t("issues.toasts.issueCreated"));
    } catch (error) {
      console.error("[Issues] create issue failed", error);
      toast.error(t("issues.toasts.issueCreateFailed"));
    }
  };

  return (
    <>
      <TeamContentShell contentClassName="max-w-none">
        {selectedIssueId ? (
          <div className="flex flex-col gap-5">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-fit"
              onClick={clearIssue}
            >
              <ChevronLeft className="size-4" />
              {t("issues.actions.backToList")}
            </Button>
            <TeamIssueDetailPageClient issueId={selectedIssueId} />
          </div>
        ) : (
        <div>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div className="space-y-1.5">
            <h2 className="text-lg font-semibold text-foreground">{t("issues.title")}</h2>
            <p className="text-sm text-muted-foreground">{t("issues.subtitle")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void refresh()}
              disabled={isRefreshing}
            >
              <RefreshCw
                className={isRefreshing ? "size-4 animate-spin" : "size-4"}
              />
              {t("issues.refresh")}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setBoardDialogOpen(true)}
            >
              <Plus className="size-4" />
              {t("issues.actions.createBoard")}
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => setIssueDialogOpen(true)}
              disabled={!selectedBoardId}
            >
              <Ticket className="size-4" />
              {t("issues.actions.createIssue")}
            </Button>
          </div>
        </div>
        {!hasLoadedBoards && isRefreshing ? (
          <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-4 w-40" />
              </CardHeader>
              <CardContent className="space-y-3 pb-6">
                <Skeleton className="h-20 rounded-2xl" />
                <Skeleton className="h-20 rounded-2xl" />
                <Skeleton className="h-20 rounded-2xl" />
              </CardContent>
            </Card>
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-56" />
              </CardHeader>
              <CardContent className="space-y-4 pb-6">
                <div className="grid gap-3 md:grid-cols-3">
                  <Skeleton className="h-20 rounded-2xl" />
                  <Skeleton className="h-20 rounded-2xl" />
                  <Skeleton className="h-20 rounded-2xl" />
                </div>
                <Skeleton className="h-10 rounded-xl" />
                <Skeleton className="h-24 rounded-2xl" />
                <Skeleton className="h-24 rounded-2xl" />
              </CardContent>
            </Card>
          </div>
        ) : boardLoadFailed && boards.length === 0 ? (
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
                  <Button type="button" variant="outline" onClick={() => void refresh()}>
                    <RefreshCw className="size-4" />
                    {t("issues.actions.retryLoad")}
                  </Button>
                </EmptyContent>
              </Empty>
            </CardContent>
          </Card>
        ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <Card className="border-border/60">
            <CardHeader>
              <CardTitle>{t("issues.boardsTitle")}</CardTitle>
              <CardDescription>{t("issues.subtitle")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 pb-6">
              {boards.length === 0 ? (
                <Empty className="min-h-72 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                  <EmptyContent>
                    <EmptyMedia variant="icon">
                      <KanbanSquare className="size-5" />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>{t("issues.boardsTitle")}</EmptyTitle>
                      <EmptyDescription>
                        {t("issues.emptyBoards")}
                      </EmptyDescription>
                    </EmptyHeader>
                  </EmptyContent>
                </Empty>
              ) : (
                boards.map((board) => (
                  <button
                    key={board.board_id}
                    type="button"
                    onClick={() => setSelectedBoardId(board.board_id)}
                    className={
                      selectedBoardId === board.board_id
                        ? "w-full rounded-2xl border border-foreground/10 bg-accent/60 px-4 py-3 text-left transition"
                        : "w-full rounded-2xl border border-border/60 px-4 py-3 text-left transition hover:bg-muted/40"
                    }
                  >
                    <p className="text-sm font-medium text-foreground">{board.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {board.description || t("issues.subtitle")}
                    </p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="border-border/60">
            <CardHeader>
              <CardTitle>{selectedBoard?.name ?? t("issues.listTitle")}</CardTitle>
              <CardDescription>
                {selectedBoard?.description || t("issues.detailPlaceholder")}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pb-6">
              <div className="grid gap-3 md:grid-cols-3">
                {[
                  {
                    label: t("issues.summary.total"),
                    value: String(boardSummary.totalIssues),
                  },
                  {
                    label: t("issues.summary.aiAssigned"),
                    value: String(boardSummary.aiAssignedIssues),
                  },
                  {
                    label: t("issues.summary.running"),
                    value: String(boardSummary.runningIssues),
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-2xl border border-border/60 bg-muted/10 px-4 py-3"
                  >
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">
                      {item.label}
                    </p>
                    <p className="mt-2 text-lg font-semibold text-foreground">
                      {item.value}
                    </p>
                  </div>
                ))}
              </div>

              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={t("issues.searchPlaceholder")}
              />

              {issuesLoadFailed ? (
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
                      onClick={() => void loadIssues()}
                    >
                      <RefreshCw className="size-4" />
                      {t("issues.actions.retryLoad")}
                    </Button>
                  </EmptyContent>
                </Empty>
              ) : issues.length === 0 ? (
                <Empty className="min-h-72 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                  <EmptyContent>
                    <EmptyMedia variant="icon">
                      <Ticket className="size-5" />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>{t("issues.listTitle")}</EmptyTitle>
                      <EmptyDescription>
                        {selectedBoardId
                          ? t("issues.emptyIssues")
                          : t("issues.emptyBoards")}
                      </EmptyDescription>
                    </EmptyHeader>
                  </EmptyContent>
                </Empty>
              ) : filteredIssues.length === 0 ? (
                <Empty className="min-h-56 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                  <EmptyContent>
                    <EmptyMedia variant="icon">
                      <Ticket className="size-5" />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>{t("issues.listTitle")}</EmptyTitle>
                      <EmptyDescription>
                        {t("issues.emptySearch")}
                      </EmptyDescription>
                    </EmptyHeader>
                  </EmptyContent>
                </Empty>
              ) : (
                filteredIssues.map((issue) => (
                  <button
                    key={issue.issue_id}
                    type="button"
                    onClick={() => selectIssue(issue.issue_id)}
                    className="block w-full rounded-2xl border border-border/60 px-4 py-4 text-left transition hover:bg-muted/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{issue.title}</p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <Badge variant="outline">
                            {formatIssueStatus(t, issue.status)}
                          </Badge>
                          <Badge variant="outline">
                            {formatIssuePriority(t, issue.priority)}
                          </Badge>
                          {issue.related_project_id ? (
                            <Badge variant="secondary">
                              {t("issues.fields.project")}
                            </Badge>
                          ) : null}
                          {issue.agent_assignment ? (
                            <AssignmentBadge assignment={issue.agent_assignment} />
                          ) : null}
                        </div>
                        <p className="mt-3 text-xs text-muted-foreground">
                          {t("issues.fields.updatedAt")} · {formatDateTime(issue.updated_at)}
                        </p>
                      </div>
                    </div>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>
        )}
        </div>
        )}
      </TeamContentShell>

      <CreateBoardDialog
        open={boardDialogOpen}
        onOpenChange={setBoardDialogOpen}
        onCreate={createBoard}
      />
      <CreateIssueDialog
        open={issueDialogOpen}
        onOpenChange={setIssueDialogOpen}
        boardName={selectedBoard?.name ?? null}
        onCreate={createIssue}
      />
    </>
  );
}

export function TeamIssueDetailPageClient({ issueId }: { issueId: string }) {
  const { t } = useT("translation");
  const lng = useLanguage();
  const router = useRouter();
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
      setPresets(nextPresets.filter((item) => item.scope !== "personal" || item.user_id));
      setProjects(nextProjects);
      setSelectedPresetId(
        nextIssue.assignee_preset_id ? String(nextIssue.assignee_preset_id) : "none",
      );
      setTriggerMode(
        nextIssue.agent_assignment?.trigger_mode ?? "persistent_sandbox",
      );
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
    if (!issue) return;
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
        related_project_id:
          relatedProjectId === "none" ? null : relatedProjectId,
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
      const result =
        action === "trigger"
          ? await issuesApi.triggerAssignment(issueId)
          : action === "retry"
            ? await issuesApi.retryAssignment(issueId)
            : action === "cancel"
              ? await issuesApi.cancelAssignment(issueId)
              : await issuesApi.releaseAssignment(issueId);
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
      if (action !== "release" && result.assignment.session_id) {
        router.refresh();
      }
    } catch (error) {
      console.error(`[Issues] ${action} assignment failed`, error);
      toast.error(t("issues.toasts.actionFailed"));
    }
  };

  const assignment = issue?.agent_assignment;
  const executionMeta = getAssignmentExecutionMeta(assignment);

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div className="space-y-1.5">
          <h2 className="text-lg font-semibold text-foreground">{issue?.title ?? t("issues.detailTitle")}</h2>
          <p className="text-sm text-muted-foreground">
            {issue
              ? t("issues.detailSubtitle", { issueId })
              : t("issues.subtitle")}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void load()}
          disabled={isLoading}
        >
          <RefreshCw className={isLoading ? "size-4 animate-spin" : "size-4"} />
          {t("issues.refresh")}
        </Button>
      </div>
      {isLoading && !issue ? (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-28" />
                <Skeleton className="h-4 w-40" />
              </CardHeader>
              <CardContent className="space-y-4 pb-6">
                <div className="flex gap-2">
                  <Skeleton className="h-6 w-20 rounded-full" />
                  <Skeleton className="h-6 w-20 rounded-full" />
                  <Skeleton className="h-6 w-24 rounded-full" />
                </div>
                <Skeleton className="h-16 rounded-2xl" />
                <Skeleton className="h-10 rounded-xl" />
              </CardContent>
            </Card>
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-36" />
                <Skeleton className="h-4 w-56" />
              </CardHeader>
              <CardContent className="space-y-4 pb-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <Skeleton className="h-10 rounded-xl" />
                  <Skeleton className="h-10 rounded-xl" />
                </div>
                <Skeleton className="h-10 rounded-xl" />
                <Skeleton className="h-10 w-40 rounded-xl" />
              </CardContent>
            </Card>
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-56" />
              </CardHeader>
              <CardContent className="pb-6">
                <Skeleton className="h-40 rounded-2xl" />
              </CardContent>
            </Card>
          </div>
          <div className="space-y-6">
            <Card className="border-border/60">
              <CardHeader>
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-4 w-40" />
              </CardHeader>
              <CardContent className="space-y-4 pb-6">
                <Skeleton className="h-48 rounded-2xl" />
                <Skeleton className="h-32 rounded-2xl" />
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
                  {t("issues.detailSubtitle", { issueId })}
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
                  <Select value={relatedProjectId} onValueChange={setRelatedProjectId}>
                    <SelectTrigger>
                      <SelectValue placeholder={t("issues.placeholders.project")} />
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
                    <Select value={selectedPresetId} onValueChange={setSelectedPresetId}>
                      <SelectTrigger>
                        <SelectValue placeholder={t("issues.placeholders.preset")} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">{t("issues.none")}</SelectItem>
                        {presets.map((preset) => (
                          <SelectItem key={preset.preset_id} value={String(preset.preset_id)}>
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
                    <Select value={triggerMode} onValueChange={(value) => setTriggerMode(value as typeof triggerMode)}>
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

                <Button type="button" onClick={() => void saveAssignment()} disabled={isSaving}>
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
                <CardDescription>{t("issues.subtitle")}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 pb-6">
                <div className="rounded-2xl border border-border/60 p-4">
                  <p className="text-sm font-medium">{t("issues.fields.assignmentStatus")}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {assignment
                      ? formatAssignmentStatus(t, assignment.status)
                      : t("issues.unassigned")}
                  </p>
                  <p className="mt-3 text-sm font-medium">{t("issues.fields.session")}</p>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {assignment?.session_id ?? t("issues.none")}
                  </p>
                  <p className="mt-3 text-sm font-medium">{t("issues.fields.container")}</p>
                  <p className="mt-1 break-all text-sm text-muted-foreground">
                    {assignment?.container_id ?? t("issues.none")}
                  </p>
                  <p className="mt-3 text-sm font-medium">{t("issues.fields.lastTriggeredAt")}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {executionMeta.lastTriggeredAt
                      ? formatDateTime(executionMeta.lastTriggeredAt)
                      : t("issues.none")}
                  </p>
                  <p className="mt-3 text-sm font-medium">{t("issues.fields.lastCompletedAt")}</p>
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
                  <Button type="button" variant="outline" onClick={() => void runAction("retry")}>
                    {t("issues.actions.retry")}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => void runAction("cancel")}>
                    {t("issues.actions.cancel")}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => void runAction("release")}>
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
                  <p>{t("issues.preview.executionMode")}: {t(`issues.triggerModes.${triggerMode}`)}</p>
                  <p className="mt-2">
                    {executionMeta.isScheduled
                      ? `${t("issues.fields.schedule")}: ${scheduleCron || t("issues.none")}`
                      : `${t("issues.fields.container")}: ${
                          executionMeta.hasRetainedContainer
                            ? assignment?.container_id
                            : t("issues.none")
                        }`}
                  </p>
                  <p className="mt-2">
                    {executionMeta.hasSession
                      ? `${t("issues.fields.session")}: ${assignment?.session_id}`
                      : `${t("issues.preview.pendingImpact")}`}
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
    </>
  );
}
