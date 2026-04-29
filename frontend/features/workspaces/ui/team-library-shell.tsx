"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft, MoreHorizontal, Plus, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { issuesApi } from "@/features/issues/api/issues-api";
import {
  buildTeamSectionHref,
  buildTeamSections,
  type TeamSectionId,
} from "@/features/workspaces/lib/team-sections";
import { TeamRailProvider, useTeamRailContext } from "@/features/workspaces/model/team-rail-context";
import { useWorkspaceContext } from "@/features/workspaces/model/workspace-context";
import type { WorkspaceBoard } from "@/features/issues/model/types";
import { TeamSectionRail } from "@/features/workspaces/ui/team-section-rail";

interface CreateWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateWorkspaceDialog({
  open,
  onOpenChange,
}: CreateWorkspaceDialogProps) {
  const { t } = useT("translation");
  const { createWorkspace } = useWorkspaceContext();
  const [name, setName] = React.useState("");
  const [isCreating, setIsCreating] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setName("");
      setIsCreating(false);
    }
  }, [open]);

  const handleCreate = async () => {
    setIsCreating(true);
    const created = await createWorkspace(name);
    setIsCreating(false);
    if (created) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("workspaces.create.dialogTitle")}</DialogTitle>
          <DialogDescription>
            {t("workspaces.create.dialogDescription")}
          </DialogDescription>
        </DialogHeader>
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t("workspaces.create.placeholder")}
          autoFocus
        />
        <DialogFooter>
          <Button
            type="button"
            onClick={() => void handleCreate()}
            disabled={isCreating || !name.trim()}
          >
            {t("workspaces.create.action")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function resolveSectionFromPath(pathname: string): TeamSectionId {
  if (pathname.includes("/members")) return "members";
  if (pathname.includes("/issues")) return "issues";
  return "overview";
}

interface TeamLibraryShellProps {
  children: React.ReactNode;
}

function TeamLibraryShellContent({ children }: TeamLibraryShellProps) {
  const { t } = useT("translation");
  const lng = useLanguage();
  const pathname = usePathname();
  const router = useRouter();
  const {
    workspaces,
    currentWorkspace,
    currentWorkspaceId,
    isLoading,
    selectWorkspace,
  } = useWorkspaceContext();
  const { railContent } = useTeamRailContext();
  const [createOpen, setCreateOpen] = React.useState(false);
  const [workspaceBoards, setWorkspaceBoards] = React.useState<
    Array<{ board: WorkspaceBoard; pendingCount: number; totalCount: number }>
  >([]);

  const activeSection = React.useMemo(
    () => resolveSectionFromPath(pathname),
    [pathname],
  );

  const isMobileDetail = React.useMemo(
    () => activeSection !== "overview",
    [activeSection],
  );

  const sections = React.useMemo(
    () =>
      buildTeamSections(lng, {
        overview: t("sidebar.teamOverview"),
        members: t("workspaces.pages.members.title"),
        issues: t("issues.title"),
      }),
    [lng, t],
  );
  const visibleSections = React.useMemo(
    () => sections.filter((section) => section.id !== "issues"),
    [sections],
  );

  const handleSelectSection = React.useCallback(
    (sectionId: TeamSectionId) => {
      const href = buildTeamSectionHref(lng, sectionId);
      router.push(href);
    },
    [lng, router],
  );

  const handleMobileBack = React.useCallback(() => {
    router.push(buildTeamSectionHref(lng, "overview"));
  }, [lng, router]);

  React.useEffect(() => {
    const loadBoards = async () => {
      if (!currentWorkspace) {
        setWorkspaceBoards([]);
        return;
      }
      try {
        const boards = await issuesApi.listBoards(currentWorkspace.id);
        const issueGroups = await Promise.all(
          boards.map((board) => issuesApi.listIssues(board.board_id)),
        );
        setWorkspaceBoards(
          boards.map((board, index) => {
            const issues = issueGroups[index] ?? [];
            return {
              board,
              totalCount: issues.length,
              pendingCount: issues.filter(
                (issue) => issue.status !== "done" && issue.status !== "canceled",
              ).length,
            };
          }),
        );
      } catch {
        setWorkspaceBoards([]);
      }
    };

    void loadBoards();
  }, [currentWorkspace]);

  const defaultRailFooter = React.useMemo(() => {
    if (!currentWorkspace) {
      return null;
    }

    return (
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
            onClick={() => router.push(`/${lng}/team/issues`)}
            aria-label={t("issues.actions.createBoard")}
          >
            <Plus className="size-4" />
          </Button>
        </div>
        <div className="space-y-1">
          {workspaceBoards.map(({ board, pendingCount, totalCount }) => {
            const isSelected =
              pathname.includes("/team/issues") &&
              pathname.includes(`board=${board.board_id}`);
            return (
              <button
                key={board.board_id}
                type="button"
                onClick={() =>
                  router.push(`/${lng}/team/issues?board=${board.board_id}`)
                }
                className={
                  isSelected
                    ? "group/board-item flex w-full flex-col rounded-md bg-muted px-3 py-2 text-left"
                    : "group/board-item flex w-full flex-col rounded-md px-3 py-2 text-left text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                }
              >
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="size-2 rounded-full bg-primary/70" />
                      <span className="truncate text-sm font-medium text-foreground">
                        {board.name}
                      </span>
                    </div>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {pendingCount} pending · {totalCount} total
                    </span>
                  </div>
                  <div className="flex items-center gap-0.5 opacity-100 transition-opacity md:opacity-0 md:group-hover/board-item:opacity-100 md:group-focus-within/board-item:opacity-100">
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      onClick={(event) => {
                        event.stopPropagation();
                        router.push(`/${lng}/team/issues?board=${board.board_id}`);
                      }}
                      aria-label={t("issues.actions.createIssue")}
                    >
                      <Plus className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      className="size-7"
                      onClick={(event) => {
                        event.stopPropagation();
                        router.push(`/${lng}/team/issues?board=${board.board_id}`);
                      }}
                      aria-label={t("issues.actions.boardSettings")}
                    >
                      <MoreHorizontal className="size-3.5" />
                    </Button>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    );
  }, [currentWorkspace, lng, pathname, router, t, workspaceBoards]);

  const headerTitle = t("sidebar.team");
  const headerSubtitle = currentWorkspace
    ? t("workspaces.currentWorkspace", { name: currentWorkspace.name })
    : t("workspaces.noWorkspace");

  const mobileBackButton = isMobileDetail ? (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="text-muted-foreground md:hidden"
      aria-label={t("workspaces.mobile.back")}
      title={t("workspaces.mobile.back")}
      onClick={handleMobileBack}
    >
      <ChevronLeft className="size-4" />
    </Button>
  ) : null;

  return (
    <>
      <PageHeaderShell
        mobileLeading={mobileBackButton ?? undefined}
        hideSidebarTrigger={isMobileDetail}
        left={
          <div className="min-w-0 flex items-center gap-3">
            <Users
              className="hidden size-5 text-muted-foreground md:block"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <p className="text-base font-semibold leading-tight">
                {headerTitle}
              </p>
              <p className="text-xs text-muted-foreground">
                {headerSubtitle}
              </p>
            </div>
          </div>
        }
        right={
          <div className="flex items-center gap-2">
            <Select
              value={currentWorkspaceId ?? undefined}
              onValueChange={selectWorkspace}
              disabled={isLoading || workspaces.length === 0}
            >
              <SelectTrigger className="w-44">
                <SelectValue
                  placeholder={t("workspaces.switcher.placeholder")}
                />
              </SelectTrigger>
              <SelectContent>
                {workspaces.map((workspace) => (
                  <SelectItem key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setCreateOpen(true)}
            >
              {t("workspaces.create.action")}
            </Button>
          </div>
        }
      />

      {/* Desktop: sidebar + detail pane */}
      <div className="hidden min-h-0 flex-1 md:grid md:grid-cols-[240px_minmax(0,1fr)]">
        <TeamSectionRail
          sections={visibleSections}
          activeSectionId={activeSection}
          onSelect={handleSelectSection}
          footer={railContent ?? defaultRailFooter}
        />
        <main className="min-h-0 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Mobile: section list or detail */}
      <div className="flex min-h-0 flex-1 md:hidden">
        {isMobileDetail ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 overflow-y-auto">
              {children}
            </div>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <TeamSectionRail
              sections={visibleSections}
              activeSectionId={activeSection}
              onSelect={handleSelectSection}
              footer={railContent ?? defaultRailFooter}
              variant="mobile"
            />
          </div>
        )}
      </div>

      <CreateWorkspaceDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </>
  );
}

export function TeamLibraryShell({ children }: TeamLibraryShellProps) {
  return (
    <TeamRailProvider>
      <TeamLibraryShellContent>{children}</TeamLibraryShellContent>
    </TeamRailProvider>
  );
}
