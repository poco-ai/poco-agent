"use client";

import * as React from "react";
import { KanbanSquare, Plus, Ticket } from "lucide-react";
import { toast } from "sonner";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useT } from "@/lib/i18n/client";
import { issuesApi } from "@/features/issues/api/issues-api";
import type {
  WorkspaceBoard,
  WorkspaceIssue,
} from "@/features/issues/model/types";
import { useWorkspaceContext } from "@/features/workspaces";

export function TeamIssuesPageClient() {
  const { t } = useT("translation");
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
              <p className="text-xs text-muted-foreground">
                {t("issues.subtitle")}
              </p>
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
                <p className="text-sm text-muted-foreground">
                  {t("issues.emptyBoards")}
                </p>
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
                <p className="text-sm text-muted-foreground">
                  {t("issues.emptyIssues")}
                </p>
              ) : (
                issues.map((issue) => (
                  <div
                    key={issue.issue_id}
                    className="rounded-xl border border-border/60 px-4 py-3"
                  >
                    <p className="font-medium">{issue.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {issue.status} · {issue.priority}
                    </p>
                  </div>
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
      <main className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="mx-auto max-w-4xl">
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              {t("issues.detailPlaceholder")}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
