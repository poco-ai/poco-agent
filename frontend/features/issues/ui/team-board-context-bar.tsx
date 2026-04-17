"use client";

import { Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { WorkspaceBoard } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";

interface TeamBoardContextBarProps {
  boards: WorkspaceBoard[];
  selectedBoardId: string | null;
  selectedBoard: WorkspaceBoard | null;
  totalIssues: number;
  aiAssignedIssues: number;
  runningIssues: number;
  isRefreshing: boolean;
  onBoardChange: (boardId: string) => void;
  onRefresh: () => void;
  onCreateBoard: () => void;
}

export function TeamBoardContextBar({
  boards,
  selectedBoardId,
  selectedBoard,
  totalIssues,
  aiAssignedIssues,
  runningIssues,
  isRefreshing,
  onBoardChange,
  onRefresh,
  onCreateBoard,
}: TeamBoardContextBarProps) {
  const { t } = useT("translation");

  return (
    <section className="rounded-[32px] border border-border/70 bg-card px-5 py-5 shadow-sm sm:px-6">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0 space-y-4">
            <div className="space-y-1.5">
              <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                {t("issues.context.eyebrow")}
              </p>
              <div className="space-y-1">
                <h2 className="text-2xl font-semibold text-foreground">
                  {selectedBoard?.name ?? t("issues.context.noBoardTitle")}
                </h2>
                <p className="max-w-2xl text-sm text-muted-foreground">
                  {selectedBoard?.description ||
                    t("issues.context.noBoardDescription")}
                </p>
              </div>
            </div>

            <div className="max-w-sm space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                {t("issues.context.boardSelectLabel")}
              </p>
              <Select
                value={selectedBoardId ?? undefined}
                onValueChange={onBoardChange}
                disabled={boards.length === 0}
              >
                <SelectTrigger className="w-full">
                  <SelectValue
                    placeholder={t("issues.context.boardSelectPlaceholder")}
                  />
                </SelectTrigger>
                <SelectContent>
                  {boards.map((board) => (
                    <SelectItem key={board.board_id} value={board.board_id}>
                      {board.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCreateBoard}
            >
              <Plus className="size-4" />
              {t("issues.actions.createBoard")}
            </Button>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {[
            {
              label: t("issues.summary.total"),
              value: String(totalIssues),
            },
            {
              label: t("issues.summary.aiAssigned"),
              value: String(aiAssignedIssues),
            },
            {
              label: t("issues.summary.running"),
              value: String(runningIssues),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-3xl border border-border/70 bg-background/80 px-4 py-4"
            >
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
                {item.label}
              </p>
              <p className="mt-3 text-2xl font-semibold text-foreground">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
