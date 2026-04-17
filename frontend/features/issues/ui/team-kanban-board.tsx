"use client";

import * as React from "react";

import {
  buildKanbanColumns,
  getNextMobileKanbanStatus,
} from "@/features/issues/lib/kanban-columns";
import { formatIssueStatus } from "@/features/issues/lib/issue-presentation";
import type { WorkspaceIssue } from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { TeamKanbanColumn } from "./team-kanban-column";

interface TeamKanbanBoardProps {
  issues: WorkspaceIssue[];
  onOpenIssue: (issueId: string) => void;
}

export function TeamKanbanBoard({
  issues,
  onOpenIssue,
}: TeamKanbanBoardProps) {
  const { t } = useT("translation");
  const columns = React.useMemo(() => buildKanbanColumns(issues), [issues]);
  const [mobileStatus, setMobileStatus] = React.useState(
    getNextMobileKanbanStatus(undefined),
  );

  React.useEffect(() => {
    setMobileStatus((currentStatus) => getNextMobileKanbanStatus(currentStatus));
  }, [columns]);

  const activeMobileColumn =
    columns.find((column) => column.status === mobileStatus) ?? columns[0];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 md:hidden">
        {columns.map((column) => (
          <button
            key={column.status}
            type="button"
            onClick={() => setMobileStatus(column.status)}
            className={cn(
              "rounded-2xl border px-3 py-2 text-left transition",
              mobileStatus === column.status
                ? "border-foreground/15 bg-accent/70 text-foreground"
                : "border-border/70 bg-background text-muted-foreground hover:bg-muted/20",
            )}
          >
            <p className="text-sm font-medium">
              {formatIssueStatus(t, column.status)}
            </p>
            <p className="text-xs">{column.issues.length}</p>
          </button>
        ))}
      </div>

      <div className="md:hidden">
        <TeamKanbanColumn
          status={activeMobileColumn.status}
          issues={activeMobileColumn.issues}
          onOpenIssue={onOpenIssue}
        />
      </div>

      <div className="hidden gap-4 overflow-x-auto pb-2 md:flex">
        {columns.map((column) => (
          <TeamKanbanColumn
            key={column.status}
            status={column.status}
            issues={column.issues}
            onOpenIssue={onOpenIssue}
            className="w-[20rem] shrink-0"
          />
        ))}
      </div>
    </div>
  );
}
