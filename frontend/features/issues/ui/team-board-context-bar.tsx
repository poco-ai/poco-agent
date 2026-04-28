"use client";

import { ChevronDown, MoreHorizontal, Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { WorkspaceBoard } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";

import { LANE_COLORS, hashCode } from "./team-kanban-board";

interface TeamBoardContextBarProps {
  boards: WorkspaceBoard[];
  selectedBoard: WorkspaceBoard | null;
  onSelectBoard: (boardId: string) => void;
  isRefreshing: boolean;
  onRefresh: () => void;
  onCreateIssue: (boardId: string) => void;
  onOpenBoardSettings: (boardId: string) => void;
  onCreateBoard: () => void;
}

export function TeamBoardContextBar({
  boards,
  selectedBoard,
  onSelectBoard,
  isRefreshing,
  onRefresh,
  onCreateIssue,
  onOpenBoardSettings,
  onCreateBoard,
}: TeamBoardContextBarProps) {
  const { t } = useT("translation");
  const boardColor = selectedBoard
    ? LANE_COLORS[Math.abs(hashCode(selectedBoard.board_id)) % LANE_COLORS.length]
    : undefined;

  return (
    <section className="overflow-hidden rounded-xl border border-border/70 bg-card shadow-sm">
      <div className="flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-foreground">
            {t("issues.title")}
          </h1>
          {boards.length > 0 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-medium text-muted-foreground transition hover:bg-muted/60 hover:text-foreground"
                >
                  {selectedBoard ? (
                    <>
                      <span
                        className="size-2 rounded-full"
                        style={{ backgroundColor: boardColor }}
                      />
                      {selectedBoard.name}
                    </>
                  ) : (
                    t("issues.selectBoard")
                  )}
                  <ChevronDown className="size-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                {boards.map((board) => {
                  const color =
                    LANE_COLORS[Math.abs(hashCode(board.board_id)) % LANE_COLORS.length];
                  const isActive = selectedBoard?.board_id === board.board_id;
                  return (
                    <DropdownMenuItem
                      key={board.board_id}
                      onSelect={() => onSelectBoard(board.board_id)}
                      className={isActive ? "font-medium" : ""}
                    >
                      <span
                        className="mr-2 size-2 shrink-0 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      {board.name}
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw
              className={isRefreshing ? "size-4 animate-spin" : "size-4"}
            />
            {t("issues.refresh")}
          </Button>
          {selectedBoard ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onCreateIssue(selectedBoard.board_id)}
            >
              <Plus className="size-4" />
              {t("issues.actions.createIssue")}
            </Button>
          ) : null}
          {selectedBoard ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={() => onOpenBoardSettings(selectedBoard.board_id)}
              aria-label={t("issues.actions.boardSettings")}
            >
              <MoreHorizontal className="size-4" />
            </Button>
          ) : null}
          <Button type="button" size="sm" onClick={onCreateBoard}>
            <Plus className="size-4" />
            {t("issues.actions.createBoard")}
          </Button>
        </div>
      </div>
    </section>
  );
}
