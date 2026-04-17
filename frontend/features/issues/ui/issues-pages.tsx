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
import { useT } from "@/lib/i18n/client";
import { useLanguage } from "@/hooks/use-language";
import { issuesApi } from "@/features/issues/api/issues-api";
import {
  mergeMovedIssue,
  moveKanbanIssue,
} from "@/features/issues/lib/kanban-columns";
import {
  filterIssuesByQuery,
  summarizeBoardIssues,
} from "@/features/issues/lib/issues-index-view";
import { useTeamKanban } from "@/features/issues/model/use-team-kanban";
import type {
  WorkspaceBoard,
  WorkspaceBoardInput,
  WorkspaceIssue,
  WorkspaceIssueStatus,
} from "@/features/issues/model/types";
import { TeamBoardContextBar } from "@/features/issues/ui/team-board-context-bar";
import { TeamBoardSettingsDialog } from "@/features/issues/ui/team-board-settings-dialog";
import { TeamIssueDetailDialog } from "@/features/issues/ui/team-issue-detail-dialog";
import { TeamKanbanBoard } from "@/features/issues/ui/team-kanban-board";
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
  const [boards, setBoards] = React.useState<WorkspaceBoard[]>([]);
  const [issues, setIssues] = React.useState<WorkspaceIssue[]>([]);
  const [selectedBoardId, setSelectedBoardId] = React.useState<string | null>(
    null,
  );
  const [boardDialogOpen, setBoardDialogOpen] = React.useState(false);
  const [boardSettingsOpen, setBoardSettingsOpen] = React.useState(false);
  const [issueDialogOpen, setIssueDialogOpen] = React.useState(false);
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [hasLoadedBoards, setHasLoadedBoards] = React.useState(false);
  const [boardLoadFailed, setBoardLoadFailed] = React.useState(false);
  const [issuesLoadFailed, setIssuesLoadFailed] = React.useState(false);
  const [isMovePending, setIsMovePending] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const { selectedIssueId, openIssue, closeIssue } = useTeamKanban(lng);

  const loadBoards = React.useCallback(async () => {
    if (!currentWorkspace) {
      return;
    }
    const nextBoards = await issuesApi.listBoards(currentWorkspace.id);
    setBoards(nextBoards);
    setSelectedBoardId((previousBoardId) =>
      previousBoardId &&
      nextBoards.some((board) => board.board_id === previousBoardId)
        ? previousBoardId
        : nextBoards[0]?.board_id ?? null,
    );
  }, [currentWorkspace]);

  const loadIssues = React.useCallback(async () => {
    if (!selectedBoardId) {
      setIssues([]);
      return;
    }
    setIssues(await issuesApi.listIssues(selectedBoardId));
  }, [selectedBoardId]);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) {
      return;
    }
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

  React.useEffect(() => {
    if (!selectedBoard) {
      setBoardSettingsOpen(false);
    }
  }, [selectedBoard]);

  const filteredIssues = React.useMemo(
    () => filterIssuesByQuery(issues, query),
    [issues, query],
  );
  const boardSummary = React.useMemo(() => summarizeBoardIssues(issues), [issues]);

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
    if (!selectedBoardId || !title.trim()) {
      return;
    }
    try {
      const created = await issuesApi.createIssue(selectedBoardId, {
        title: title.trim(),
      });
      setIssues((previousIssues) => [created, ...previousIssues]);
      setIssueDialogOpen(false);
      toast.success(t("issues.toasts.issueCreated"));
    } catch (error) {
      console.error("[Issues] create issue failed", error);
      toast.error(t("issues.toasts.issueCreateFailed"));
    }
  };

  const saveBoardSettings = async (input: WorkspaceBoardInput) => {
    if (!currentWorkspace || !selectedBoard) {
      return;
    }

    try {
      const updatedBoard = await issuesApi.updateBoard(
        currentWorkspace.id,
        selectedBoard.board_id,
        input,
      );
      setBoards((previousBoards) =>
        previousBoards.map((board) =>
          board.board_id === updatedBoard.board_id ? updatedBoard : board,
        ),
      );
      setBoardSettingsOpen(false);
      toast.success(t("issues.toasts.boardUpdated"));
    } catch (error) {
      console.error("[Issues] update board failed", error);
      toast.error(t("issues.toasts.boardUpdateFailed"));
    }
  };

  const deleteBoard = async () => {
    if (!currentWorkspace || !selectedBoard) {
      return;
    }

    try {
      await issuesApi.deleteBoard(currentWorkspace.id, selectedBoard.board_id);
      const deletedBoardId = selectedBoard.board_id;
      const deletedBoardIndex = boards.findIndex(
        (board) => board.board_id === deletedBoardId,
      );
      const nextBoards = boards.filter((board) => board.board_id !== deletedBoardId);
      const fallbackBoard =
        nextBoards[deletedBoardIndex] ?? nextBoards[deletedBoardIndex - 1] ?? null;

      setBoards(nextBoards);
      setSelectedBoardId(fallbackBoard?.board_id ?? null);
      setIssues([]);
      setBoardSettingsOpen(false);
      closeIssue();
      toast.success(t("issues.toasts.boardDeleted"));
    } catch (error) {
      console.error("[Issues] delete board failed", error);
      toast.error(t("issues.toasts.boardDeleteFailed"));
    }
  };

  const moveIssue = React.useCallback(
    async (issueId: string, status: WorkspaceIssueStatus, position: number) => {
      if (isMovePending) {
        return;
      }

      const previousIssues = issues;
      const optimisticIssues = moveKanbanIssue(previousIssues, {
        issueId,
        status,
        position,
      });
      if (optimisticIssues === previousIssues) {
        return;
      }

      setIssues(optimisticIssues);
      setIsMovePending(true);

      try {
        const updatedIssue = await issuesApi.moveIssue(issueId, {
          status,
          position,
        });
        setIssues((currentIssues) => mergeMovedIssue(currentIssues, updatedIssue));
      } catch (error) {
        console.error("[Issues] move issue failed", error);
        setIssues(previousIssues);
        toast.error(t("issues.toasts.issueMoveFailed"));
      } finally {
        setIsMovePending(false);
      }
    },
    [isMovePending, issues, t],
  );

  return (
    <>
      <TeamContentShell contentClassName="max-w-none">
        <div className="space-y-6">
          <TeamBoardContextBar
            boards={boards}
            selectedBoardId={selectedBoardId}
            selectedBoard={selectedBoard}
            totalIssues={boardSummary.totalIssues}
            aiAssignedIssues={boardSummary.aiAssignedIssues}
            runningIssues={boardSummary.runningIssues}
            isRefreshing={isRefreshing}
            onBoardChange={setSelectedBoardId}
            onRefresh={() => void refresh()}
            onCreateBoard={() => setBoardDialogOpen(true)}
            onOpenSettings={() => setBoardSettingsOpen(true)}
          />

          {!hasLoadedBoards && isRefreshing ? (
            <div className="space-y-6">
              <div className="rounded-[32px] border border-border/70 bg-card px-5 py-5 sm:px-6">
                <div className="grid gap-3 md:grid-cols-3">
                  <Skeleton className="h-24 rounded-3xl" />
                  <Skeleton className="h-24 rounded-3xl" />
                  <Skeleton className="h-24 rounded-3xl" />
                </div>
              </div>
              <div className="rounded-[32px] border border-border/70 bg-card px-5 py-4 sm:px-6">
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Skeleton className="h-10 flex-1 rounded-2xl" />
                  <Skeleton className="h-10 w-40 rounded-2xl" />
                </div>
              </div>
              <div className="hidden gap-4 md:flex">
                <Skeleton className="h-[28rem] w-[20rem] rounded-[28px]" />
                <Skeleton className="h-[28rem] w-[20rem] rounded-[28px]" />
                <Skeleton className="h-[28rem] w-[20rem] rounded-[28px]" />
              </div>
              <Skeleton className="h-[28rem] rounded-[28px] md:hidden" />
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
          ) : (
            <div className="space-y-6">
              <section className="rounded-[28px] border border-border/70 bg-card px-5 py-4 sm:px-6">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">
                      {t("issues.toolbar.title")}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {t("issues.toolbar.description", {
                        count: filteredIssues.length,
                      })}
                    </p>
                  </div>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <Input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder={t("issues.searchPlaceholder")}
                      className="min-w-0 sm:w-72"
                    />
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
              </section>

              {!selectedBoardId ? (
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
              ) : issuesLoadFailed ? (
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
                          onClick={() => void loadIssues()}
                        >
                          <RefreshCw className="size-4" />
                          {t("issues.actions.retryLoad")}
                        </Button>
                      </EmptyContent>
                    </Empty>
                  </CardContent>
                </Card>
              ) : issues.length === 0 ? (
                <Card className="border-border/60">
                  <CardContent className="p-6">
                    <Empty className="min-h-72 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                      <EmptyContent>
                        <EmptyMedia variant="icon">
                          <Ticket className="size-5" />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle>{t("issues.listTitle")}</EmptyTitle>
                          <EmptyDescription>
                            {t("issues.emptyIssues")}
                          </EmptyDescription>
                        </EmptyHeader>
                      </EmptyContent>
                    </Empty>
                  </CardContent>
                </Card>
              ) : filteredIssues.length === 0 ? (
                <Card className="border-border/60">
                  <CardContent className="p-6">
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
                  </CardContent>
                </Card>
              ) : (
                <TeamKanbanBoard
                  issues={filteredIssues}
                  onOpenIssue={openIssue}
                  onMoveIssue={moveIssue}
                  isMovePending={isMovePending}
                />
              )}
            </div>
          )}
        </div>
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
      <TeamBoardSettingsDialog
        board={selectedBoard}
        issueCount={boardSummary.totalIssues}
        open={boardSettingsOpen}
        onOpenChange={setBoardSettingsOpen}
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
      />
    </>
  );
}
