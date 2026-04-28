"use client";

import * as React from "react";
import { KanbanSquare, RefreshCw, Ticket } from "lucide-react";
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
import { TeamBoardContextBar } from "@/features/issues/ui/team-board-context-bar";
import { TeamBoardSettingsDialog } from "@/features/issues/ui/team-board-settings-dialog";
import { TeamIssueDetailDialog } from "@/features/issues/ui/team-issue-detail-dialog";
import { TeamKanbanBoard } from "@/features/issues/ui/team-kanban-board";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { useWorkspaceContext } from "@/features/workspaces";
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
  const { currentWorkspace } = useWorkspaceContext();
  const { selectedIssueId, openIssue, closeIssue } = useTeamKanban(lng);

  const [boards, setBoards] = React.useState<WorkspaceBoard[]>([]);
  const [issues, setIssues] = React.useState<WorkspaceIssue[]>([]);
  const [selectedBoardId, setSelectedBoardId] = React.useState<string | null>(null);
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
      setSelectedBoardId(boards[0].board_id);
    }
    if (issueBoardId && !boardIdSet.has(issueBoardId)) {
      setIssueBoardId(null);
    }
    if (boardSettingsId && !boardIdSet.has(boardSettingsId)) {
      setBoardSettingsId(null);
    }
  }, [boards, selectedBoardId, issueBoardId, boardSettingsId, boardIdSet]);

  const createBoard = async (name: string) => {
    if (!currentWorkspace || !name.trim()) {
      return;
    }
    try {
      const created = await issuesApi.createBoard(currentWorkspace.id, {
        name: name.trim(),
      });
      setBoards((previousBoards) => [created, ...previousBoards]);
      setSelectedBoardId(created.board_id);
      setBoardDialogOpen(false);
      toast.success(t("issues.toasts.boardCreated"));
    } catch (error) {
      console.error("[Issues] create board failed", error);
      toast.error(t("issues.toasts.boardCreateFailed"));
    }
  };

  const createIssue = async (title: string) => {
    if (!issueBoardId || !title.trim()) {
      return;
    }
    try {
      const created = await issuesApi.createIssue(issueBoardId, {
        title: title.trim(),
      });
      setIssues((previousIssues) => [created, ...previousIssues]);
      setIssueBoardId(null);
      toast.success(t("issues.toasts.issueCreated"));
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
          <TeamBoardContextBar
            boards={boards}
            selectedBoard={selectedBoard}
            onSelectBoard={setSelectedBoardId}
            isRefreshing={isRefreshing}
            onRefresh={() => void refresh()}
            onCreateIssue={setIssueBoardId}
            onOpenBoardSettings={setBoardSettingsId}
            onCreateBoard={() => setBoardDialogOpen(true)}
          />

          {!hasLoadedBoards && isRefreshing ? (
            <div className="space-y-6">
              <div className="border border-border/70 bg-card px-5 py-4 shadow-sm sm:px-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-7 w-28" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                  <div className="flex gap-2">
                    <Skeleton className="h-9 w-24" />
                    <Skeleton className="h-9 w-28" />
                  </div>
                </div>
              </div>
              <div className="border border-border/70 bg-card shadow-sm">
                <Skeleton className="h-48 w-full" />
              </div>
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
            <TeamKanbanBoard
              boards={boards}
              issues={issues}
              selectedBoardId={selectedBoardId}
              presetMap={presetMap}
              onOpenIssue={openIssue}
              onToggleIssueStatus={(issueId) => void toggleIssueStatus(issueId)}
              pendingIssueId={pendingIssueId}
            />
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
