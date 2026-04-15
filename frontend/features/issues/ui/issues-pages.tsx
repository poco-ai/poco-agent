"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, KanbanSquare, Plus, RefreshCw, Ticket } from "lucide-react";
import { toast } from "sonner";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { issuesApi } from "@/features/issues/api/issues-api";
import type {
  AgentAssignment,
  WorkspaceBoard,
  WorkspaceIssue,
} from "@/features/issues/model/types";
import { projectsService } from "@/features/projects/api/projects-api";
import type { ProjectItem } from "@/features/projects/types";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useWorkspaceContext } from "@/features/workspaces";

function AssignmentBadge({
  assignment,
}: {
  assignment?: AgentAssignment | null;
}) {
  if (!assignment) return null;
  return <Badge variant="secondary">{assignment.status}</Badge>;
}

export function TeamIssuesPageClient() {
  const { t } = useT("translation");
  const lng = useLanguage();
  const { currentWorkspace } = useWorkspaceContext();
  const [boards, setBoards] = React.useState<WorkspaceBoard[]>([]);
  const [issues, setIssues] = React.useState<WorkspaceIssue[]>([]);
  const [selectedBoardId, setSelectedBoardId] = React.useState<string | null>(null);
  const [boardName, setBoardName] = React.useState("");
  const [issueTitle, setIssueTitle] = React.useState("");

  React.useEffect(() => {
    const load = async () => {
      if (!currentWorkspace) return;
      try {
        const nextBoards = await issuesApi.listBoards(currentWorkspace.id);
        setBoards(nextBoards);
        setSelectedBoardId((prev) => prev ?? nextBoards[0]?.board_id ?? null);
      } catch (error) {
        console.error("[Issues] load boards failed", error);
        toast.error(t("issues.toasts.loadFailed"));
      }
    };
    void load();
  }, [currentWorkspace, t]);

  React.useEffect(() => {
    const load = async () => {
      if (!selectedBoardId) {
        setIssues([]);
        return;
      }
      try {
        setIssues(await issuesApi.listIssues(selectedBoardId));
      } catch (error) {
        console.error("[Issues] load issues failed", error);
        toast.error(t("issues.toasts.loadFailed"));
      }
    };
    void load();
  }, [selectedBoardId, t]);

  const createBoard = async () => {
    if (!currentWorkspace || !boardName.trim()) return;
    try {
      const created = await issuesApi.createBoard(currentWorkspace.id, {
        name: boardName.trim(),
      });
      setBoards((prev) => [created, ...prev]);
      setSelectedBoardId(created.board_id);
      setBoardName("");
      toast.success(t("issues.toasts.boardCreated"));
    } catch (error) {
      console.error("[Issues] create board failed", error);
      toast.error(t("issues.toasts.boardCreateFailed"));
    }
  };

  const createIssue = async () => {
    if (!selectedBoardId || !issueTitle.trim()) return;
    try {
      const created = await issuesApi.createIssue(selectedBoardId, {
        title: issueTitle.trim(),
      });
      setIssues((prev) => [created, ...prev]);
      setIssueTitle("");
      toast.success(t("issues.toasts.issueCreated"));
    } catch (error) {
      console.error("[Issues] create issue failed", error);
      toast.error(t("issues.toasts.issueCreateFailed"));
    }
  };

  return (
    <>
      <PageHeaderShell
        left={
          <div className="flex items-center gap-3">
            <KanbanSquare className="hidden size-5 text-muted-foreground md:block" />
            <div>
              <p className="text-base font-semibold">{t("issues.title")}</p>
              <p className="text-xs text-muted-foreground">{t("issues.subtitle")}</p>
            </div>
          </div>
        }
      />
      <main className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
          <Card>
            <CardHeader>
              <CardTitle>{t("issues.boardsTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={boardName}
                  onChange={(event) => setBoardName(event.target.value)}
                  placeholder={t("issues.boardNamePlaceholder")}
                />
                <Button type="button" size="icon" onClick={() => void createBoard()}>
                  <Plus className="size-4" />
                </Button>
              </div>
              {boards.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("issues.emptyBoards")}</p>
              ) : (
                boards.map((board) => (
                  <button
                    key={board.board_id}
                    type="button"
                    onClick={() => setSelectedBoardId(board.board_id)}
                    className="w-full rounded-xl border border-border/60 px-3 py-2 text-left text-sm transition hover:bg-muted/40"
                  >
                    {board.name}
                  </button>
                ))
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>{t("issues.listTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={issueTitle}
                  onChange={(event) => setIssueTitle(event.target.value)}
                  placeholder={t("issues.issueTitlePlaceholder")}
                />
                <Button type="button" size="icon" onClick={() => void createIssue()}>
                  <Ticket className="size-4" />
                </Button>
              </div>
              {issues.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("issues.emptyIssues")}</p>
              ) : (
                issues.map((issue) => (
                  <Link
                    key={issue.issue_id}
                    href={`/${lng}/team/issues/${issue.issue_id}`}
                    className="block rounded-xl border border-border/60 px-4 py-3 transition hover:bg-muted/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{issue.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {issue.status} · {issue.priority}
                        </p>
                      </div>
                      <AssignmentBadge assignment={issue.agent_assignment} />
                    </div>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </main>
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
  const [isSaving, setIsSaving] = React.useState(false);

  const load = React.useCallback(async () => {
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
      toast.error(t("issues.toasts.loadFailed"));
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

  if (!issue) {
    return (
      <>
        <PageHeaderShell
          left={
            <div>
              <p className="text-base font-semibold">{t("issues.detailTitle")}</p>
              <p className="text-xs text-muted-foreground">
                {t("issues.detailSubtitle", { issueId })}
              </p>
            </div>
          }
        />
        <main className="flex-1 overflow-auto p-4 sm:p-6" />
      </>
    );
  }

  const assignment = issue.agent_assignment;

  return (
    <>
      <PageHeaderShell
        left={
          <div>
            <p className="text-base font-semibold">{t("issues.detailTitle")}</p>
            <p className="text-xs text-muted-foreground">
              {t("issues.detailSubtitle", { issueId })}
            </p>
          </div>
        }
        right={
          <Button type="button" variant="outline" onClick={() => void load()}>
            <RefreshCw className="size-4" />
            {t("issues.refresh")}
          </Button>
        }
      />
      <main className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="mx-auto grid max-w-6xl gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <CardHeader>
              <CardTitle>{issue.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">{issue.status}</Badge>
                <Badge variant="outline">{issue.priority}</Badge>
                {assignment ? <AssignmentBadge assignment={assignment} /> : null}
              </div>
              <p className="text-sm text-muted-foreground">
                {issue.description || t("issues.emptyDescription")}
              </p>
              <div className="grid gap-4 md:grid-cols-2">
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
              </div>
              <div className="grid gap-4 md:grid-cols-2">
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
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("issues.fields.prompt")}
                </p>
                <Textarea
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  rows={10}
                  placeholder={t("issues.placeholders.prompt")}
                />
              </div>
              <Button type="button" onClick={() => void saveAssignment()} disabled={isSaving}>
                <Bot className="size-4" />
                {t("issues.actions.saveAssignment")}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("issues.executionTitle")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-xl border border-border/60 p-4">
                <p className="text-sm font-medium">{t("issues.fields.assignmentStatus")}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {assignment?.status ?? t("issues.unassigned")}
                </p>
                <p className="mt-3 text-sm font-medium">{t("issues.fields.session")}</p>
                <p className="mt-1 break-all text-sm text-muted-foreground">
                  {assignment?.session_id ?? t("issues.none")}
                </p>
                <p className="mt-3 text-sm font-medium">{t("issues.fields.container")}</p>
                <p className="mt-1 break-all text-sm text-muted-foreground">
                  {assignment?.container_id ?? t("issues.none")}
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
        </div>
      </main>
    </>
  );
}
