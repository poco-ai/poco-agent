"use client";

import * as React from "react";
import { KanbanSquare, MoreHorizontal, Plus, RefreshCw, Ticket, ChevronDown, Flag } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { issuesApi } from "@/features/issues/api/issues-api";
import { summarizeBoardIssues } from "@/features/issues/lib/issues-index-view";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { useTeamKanban } from "@/features/issues/model/use-team-kanban";
import type {
  WorkspaceBoard,
  WorkspaceBoardInput,
  WorkspaceIssue,
} from "@/features/issues/model/types";
import { TeamBoardSettingsDialog } from "@/features/issues/ui/team-board-settings-dialog";
import { TeamIssueDetailDialog } from "@/features/issues/ui/team-issue-detail-dialog";
import { TeamKanbanBoard } from "@/features/issues/ui/team-kanban-board";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { useWorkspaceContext } from "@/features/workspaces";
import { useTeamRailContext } from "@/features/workspaces/model/team-rail-context";
import { TeamContentShell } from "@/features/workspaces/ui/team-content-shell";

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

interface CreateIssueInput {
  title: string;
  description: string;
  priority: string;
}

interface CreateIssueDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  boardName: string | null;
  onCreate: (input: CreateIssueInput) => Promise<void>;
}

const PRIORITY_OPTIONS = [
  { value: "high", iconClass: "text-red-500" },
  { value: "medium", iconClass: "text-amber-500" },
  { value: "low", iconClass: "text-muted-foreground" },
] as const;

function CreateIssueDialog({
  open,
  onOpenChange,
  boardName,
  onCreate,
}: CreateIssueDialogProps) {
  const { t } = useT("translation");
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [priority, setPriority] = React.useState("low");
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setTitle("");
      setDescription("");
      setPriority("low");
      setIsSaving(false);
    }
  }, [open]);

  const handleCreate = async () => {
    setIsSaving(true);
    await onCreate({ title, description, priority });
    setIsSaving(false);
  };

  const selectedPriority = PRIORITY_OPTIONS.find((o) => o.value === priority) ?? PRIORITY_OPTIONS[1];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("issues.dialogs.createIssueTitle")}</DialogTitle>
          <DialogDescription>
            {boardName ?? t("issues.emptyBoards")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={t("issues.issueTitlePlaceholder")}
            autoFocus
          />
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={t("issues.placeholders.description")}
            rows={3}
            className="rounded-xl border-border/50 bg-background/80 shadow-none"
          />
          <div className="flex items-center gap-3">
            <p className="text-xs font-medium text-muted-foreground">
              {t("issues.fields.priority")}
            </p>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-2 rounded-xl"
                >
                  <Flag className={`size-3.5 ${selectedPriority.iconClass}`} />
                  <span>{t(`issues.priorities.${priority}`)}</span>
                  <ChevronDown className="size-3.5 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="z-[80] min-w-36">
                {PRIORITY_OPTIONS.map((option) => (
                  <DropdownMenuItem
                    key={option.value}
                    onSelect={() => setPriority(option.value)}
                  >
                    <Flag className={`size-3.5 ${option.iconClass}`} />
                    {t(`issues.priorities.${option.value}`)}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
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
  const { setRailContent } = useTeamRailContext();
  const { selectedIssueId, openIssue, closeIssue } = useTeamKanban(lng);
  const queryBoardId = searchParams.get("board");

  const [boards, setBoards] = React.useState<WorkspaceBoard[]>([]);
  const [issues, setIssues] = React.useState<WorkspaceIssue[]>([]);
  const [boardDialogOpen, setBoardDialogOpen] = React.useState(false);
  const [issueBoardId, setIssueBoardId] = React.useState<string | null>(null);
  const [boardSettingsId, setBoardSettingsId] = React.useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [hasLoadedBoards, setHasLoadedBoards] = React.useState(false);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [pendingIssueId, setPendingIssueId] = React.useState<string | null>(null);
  const [presets, setPresets] = React.useState<Preset[]>([]);

  const presetMap = React.useMemo(
    () => new Map(presets.map((p) => [p.preset_id, p])),
    [presets],
  );

  const issueBoard = React.useMemo(
    () => boards.find((board) => board.board_id === issueBoardId) ?? null,
    [boards, issueBoardId],
  );
  const selectedBoardId = React.useMemo(
    () => queryBoardId ?? boards[0]?.board_id ?? null,
    [boards, queryBoardId],
  );
  const selectedBoard = React.useMemo(
    () => boards.find((board) => board.board_id === selectedBoardId) ?? boards[0] ?? null,
    [boards, selectedBoardId],
  );
  const settingsBoard = React.useMemo(
    () => boards.find((board) => board.board_id === boardSettingsId) ?? null,
    [boards, boardSettingsId],
  );
  const settingsBoardIssueCount = React.useMemo(
    () =>
      settingsBoard
        ? summarizeBoardIssues(
            issues.filter((issue) => issue.board_id === settingsBoard.board_id),
          ).totalIssues
        : 0,
    [issues, settingsBoard],
  );
  const boardStats = React.useMemo(
    () =>
      boards.map((board) => {
        const boardIssues = issues.filter((issue) => issue.board_id === board.board_id);
        const pendingCount = boardIssues.filter(
          (issue) => issue.status !== "done" && issue.status !== "canceled",
        ).length;
        return {
          board,
          totalCount: boardIssues.length,
          pendingCount,
        };
      }),
    [boards, issues],
  );

  const selectBoard = React.useCallback(
    (boardId: string) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("board", boardId);
      const query = params.toString();
      router.replace(`/${lng}/team/issues${query ? `?${query}` : ""}`, {
        scroll: false,
      });
    },
    [lng, router, searchParams],
  );

  const boardRailContent = React.useMemo(
    () => (
      <section className="space-y-2">
        <div className="flex items-center justify-between px-2">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            {t("issues.boardsTitle")}
          </p>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-8"
            onClick={() => setBoardDialogOpen(true)}
            aria-label={t("issues.actions.createBoard")}
          >
            <Plus className="size-4" />
          </Button>
        </div>
        <div className="space-y-1">
          {boardStats.map(({ board, totalCount, pendingCount }) => {
            const isActive = selectedBoard?.board_id === board.board_id;
            return (
              <div
                key={board.board_id}
                className={`rounded-md px-3 py-2 transition ${
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                } group/board-item`}
              >
                <div className="flex items-start gap-2">
                  <button
                    type="button"
                    onClick={() => selectBoard(board.board_id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <span className="size-2 rounded-full bg-primary/70" />
                      <span className="truncate text-sm font-medium text-foreground">
                        {board.name}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {pendingCount} pending · {totalCount} total
                    </p>
                  </button>
                  <div className="flex items-center gap-0.5 opacity-100 transition-opacity md:opacity-0 md:group-hover/board-item:opacity-100 md:group-focus-within/board-item:opacity-100">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      onClick={() => setIssueBoardId(board.board_id)}
                      aria-label={t("issues.actions.createIssue")}
                    >
                      <Plus className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      onClick={() => setBoardSettingsId(board.board_id)}
                      aria-label={t("issues.actions.boardSettings")}
                    >
                      <MoreHorizontal className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    ),
    [boardStats, selectBoard, selectedBoard, t],
  );

  const mergeIssue = React.useCallback((updatedIssue: WorkspaceIssue) => {
    setIssues((currentIssues) => {
      const hasExisting = currentIssues.some(
        (issue) => issue.issue_id === updatedIssue.issue_id,
      );
      if (!hasExisting) {
        return [updatedIssue, ...currentIssues];
      }
      return currentIssues.map((issue) =>
        issue.issue_id === updatedIssue.issue_id ? updatedIssue : issue,
      );
    });
  }, []);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) {
      return;
    }

    setIsRefreshing(true);
    setLoadFailed(false);
    try {
      const [nextBoards, nextPresets] = await Promise.all([
        issuesApi.listBoards(currentWorkspace.id),
        presetsService.listPresets(),
      ]);
      const nextIssueGroups = await Promise.all(
        nextBoards.map((board) => issuesApi.listIssues(board.board_id)),
      );
      setBoards(nextBoards);
      setIssues(nextIssueGroups.flat());
      setPresets(
        nextPresets.filter((p) => p.scope !== "personal" || p.user_id),
      );
      setHasLoadedBoards(true);
    } catch (error) {
      console.error("[Issues] refresh failed", error);
      setLoadFailed(true);
      toast.error(t("issues.toasts.loadFailed"));
    } finally {
      setIsRefreshing(false);
    }
  }, [currentWorkspace, t]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const boardIdSet = React.useMemo(
    () => new Set(boards.map((b) => b.board_id)),
    [boards],
  );

  React.useEffect(() => {
    if (boards.length > 0 && selectedBoardId && !boardIdSet.has(selectedBoardId)) {
      selectBoard(boards[0].board_id);
      return;
    }
    if (boards.length > 0 && !queryBoardId) {
      selectBoard(boards[0].board_id);
      return;
    }
    if (issueBoardId && !boardIdSet.has(issueBoardId)) {
      setIssueBoardId(null);
    }
    if (boardSettingsId && !boardIdSet.has(boardSettingsId)) {
      setBoardSettingsId(null);
    }
  }, [
    boards,
    selectedBoardId,
    queryBoardId,
    issueBoardId,
    boardSettingsId,
    boardIdSet,
    selectBoard,
  ]);

  React.useLayoutEffect(() => {
    if (boards.length === 0) {
      return;
    }

    setRailContent(boardRailContent);
    return () => setRailContent(null);
  }, [boardRailContent, boards.length, setRailContent]);

  const createBoard = async (name: string) => {
    if (!currentWorkspace || !name.trim()) {
      return;
    }
    try {
      const created = await issuesApi.createBoard(currentWorkspace.id, {
        name: name.trim(),
      });
      setBoards((previousBoards) => [created, ...previousBoards]);
      selectBoard(created.board_id);
      setBoardDialogOpen(false);
      toast.success(t("issues.toasts.boardCreated"));
    } catch (error) {
      console.error("[Issues] create board failed", error);
      toast.error(t("issues.toasts.boardCreateFailed"));
    }
  };

  const createIssue = async (input: CreateIssueInput) => {
    if (!issueBoardId || !input.title.trim()) {
      return;
    }
    try {
      await issuesApi.createIssue(issueBoardId, {
        title: input.title.trim(),
        description: input.description.trim() || null,
        priority: input.priority,
      });
      setIssueBoardId(null);
      toast.success(t("issues.toasts.issueCreated"));
      const refetched = await issuesApi.listIssues(issueBoardId);
      setIssues((prev) => [
        ...refetched,
        ...prev.filter((i) => i.board_id !== issueBoardId),
      ]);
    } catch (error) {
      console.error("[Issues] create issue failed", error);
      toast.error(t("issues.toasts.issueCreateFailed"));
    }
  };

  const saveBoardSettings = async (input: WorkspaceBoardInput) => {
    if (!currentWorkspace || !settingsBoard) {
      return;
    }

    try {
      const updatedBoard = await issuesApi.updateBoard(
        currentWorkspace.id,
        settingsBoard.board_id,
        input,
      );
      setBoards((previousBoards) =>
        previousBoards.map((board) =>
          board.board_id === updatedBoard.board_id ? updatedBoard : board,
        ),
      );
      setBoardSettingsId(null);
      toast.success(t("issues.toasts.boardUpdated"));
    } catch (error) {
      console.error("[Issues] update board failed", error);
      toast.error(t("issues.toasts.boardUpdateFailed"));
    }
  };

  const deleteBoard = async () => {
    if (!currentWorkspace || !settingsBoard) {
      return;
    }

    try {
      await issuesApi.deleteBoard(currentWorkspace.id, settingsBoard.board_id);
      setBoards((previousBoards) =>
        previousBoards.filter((board) => board.board_id !== settingsBoard.board_id),
      );
      setIssues((previousIssues) =>
        previousIssues.filter((issue) => issue.board_id !== settingsBoard.board_id),
      );
      setBoardSettingsId(null);
      closeIssue();
      toast.success(t("issues.toasts.boardDeleted"));
    } catch (error) {
      console.error("[Issues] delete board failed", error);
      toast.error(t("issues.toasts.boardDeleteFailed"));
    }
  };

  const toggleIssueStatus = React.useCallback(
    async (issueId: string) => {
      const issue = issues.find((item) => item.issue_id === issueId);
      if (!issue || pendingIssueId) {
        return;
      }

      setPendingIssueId(issueId);
      try {
        const updated = await issuesApi.updateIssue(issue.board_id, issue.issue_id, {
          status: issue.status === "done" || issue.status === "canceled" ? "todo" : "done",
        });
        mergeIssue(updated);
      } catch (error) {
        console.error("[Issues] toggle issue status failed", error);
        toast.error(t("issues.toasts.issueUpdateFailed"));
      } finally {
        setPendingIssueId(null);
      }
    },
    [issues, mergeIssue, pendingIssueId, t],
  );

  return (
    <>
      <TeamContentShell contentClassName="max-w-none">
        <div className="space-y-6">
          {!hasLoadedBoards && isRefreshing ? (
            <div className="space-y-4">
              <Skeleton className="h-10 w-40 rounded-lg" />
              <Skeleton className="h-48 w-full" />
            </div>
          ) : loadFailed && boards.length === 0 ? (
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
                      onClick={() => void refresh()}
                    >
                      <RefreshCw className="size-4" />
                      {t("issues.actions.retryLoad")}
                    </Button>
                  </EmptyContent>
                </Empty>
              </CardContent>
            </Card>
          ) : boards.length === 0 ? (
            <Card className="border-border/60">
              <CardContent className="p-6">
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
              </CardContent>
            </Card>
          ) : (
            <section className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <h2 className="text-2xl font-semibold text-foreground">
                    {selectedBoard?.name ?? t("issues.boardsTitle")}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {selectedBoard?.description || t("issues.emptyDescription")}
                  </p>
                </div>
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
              </div>

              <TeamKanbanBoard
                boards={boards}
                issues={issues}
                selectedBoardId={selectedBoardId}
                presetMap={presetMap}
                onOpenIssue={openIssue}
                onToggleIssueStatus={(issueId) => void toggleIssueStatus(issueId)}
                pendingIssueId={pendingIssueId}
              />
            </section>
          )}
        </div>
      </TeamContentShell>

      <CreateBoardDialog
        open={boardDialogOpen}
        onOpenChange={setBoardDialogOpen}
        onCreate={createBoard}
      />
      <CreateIssueDialog
        open={Boolean(issueBoardId)}
        onOpenChange={(open) => !open && setIssueBoardId(null)}
        boardName={issueBoard?.name ?? null}
        onCreate={createIssue}
      />
      <TeamBoardSettingsDialog
        board={settingsBoard}
        issueCount={settingsBoardIssueCount}
        open={Boolean(boardSettingsId)}
        onOpenChange={(open) => !open && setBoardSettingsId(null)}
        onSave={saveBoardSettings}
        onDelete={deleteBoard}
      />
      <TeamIssueDetailDialog
        issueId={selectedIssueId}
        onClose={closeIssue}
        onDeleted={(issueId) => {
          setIssues((previousIssues) =>
            previousIssues.filter((issue) => issue.issue_id !== issueId),
          );
          closeIssue();
        }}
        onUpdated={mergeIssue}
      />
    </>
  );
}
